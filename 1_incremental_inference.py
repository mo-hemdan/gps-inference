# %%
from collections import defaultdict
from math import sqrt
import psycopg

# -----------------------------
# Helpers
# -----------------------------

def time_bin(ts, T):
    """Return the time-bin index for a timestamp."""
    # Example: T = number of bins per day
    seconds = ts.hour * 3600 + ts.minute * 60 + ts.second
    return int(seconds / (86400 / T))


def init_road_state(T):
    """Create the D[r] structure."""
    return {
        "v_min": float("inf"),
        "v_max": float("-inf"),
        "d_left": float("inf"),
        "d_right": float("-inf"),

        "n_d": 0,
        "mu_d": 0.0,
        "M_d": 0.0,

        "n_forward": 0,
        "n_backward": 0,

        "v": {
            t: {"n": 0, "mu": 0.0, "M": 0.0}
            for t in range(T)
        }
    }

# %%

# -----------------------------
# DB update functions
# -----------------------------

def update_metadata_table(conn, D):
    with conn.cursor() as cur:
        for r, s in D.items():
            sigma_d = sqrt(s["M_d"] / s["n_d"]) if s["n_d"] > 0 else None

            cur.execute("""
                UPDATE metadata_table
                SET v_min = LEAST(v_min, %s),
                    v_max = GREATEST(v_max, %s),
                    d_left = LEAST(d_left, %s),
                    d_right = GREATEST(d_right, %s),
                    mu_d = %s,
                    sigma_d = %s,
                    n_forward = n_forward + %s,
                    n_backward = n_backward + %s
                WHERE road_id = %s
            """, (
                s["v_min"], s["v_max"],
                s["d_left"], s["d_right"],
                s["mu_d"], sigma_d,
                s["n_forward"], s["n_backward"],
                r
            ))
    conn.commit()


def update_temp_table(conn, D):
    with conn.cursor() as cur:
        for r, s in D.items():
            for t, vt in s["v"].items():
                if vt["n"] == 0:
                    continue

                sigma = sqrt(vt["M"] / vt["n"])

                cur.execute("""
                    INSERT INTO intermediate_table
                    (road_id, time_bin, n, mu, sigma)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (road_id, time_bin)
                    DO UPDATE SET
                        n = intermediate_table.n + EXCLUDED.n,
                        mu = EXCLUDED.mu,
                        sigma = EXCLUDED.sigma
                """, (r, t, vt["n"], vt["mu"], sigma))
    conn.commit()


# -----------------------------
# Main procedure
# -----------------------------

def infer_from_gps(conn, batch_size=100_000, T=24):

    # Server-side cursor → stream rows without loading whole table
    with conn.cursor(name="gps_cursor") as cur:

        cur.execute("""
            SELECT road_id, timestamp, speed, signed_d, direction
            FROM mapmatched_points
            ORDER BY id
        """)

        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break

            D = defaultdict(lambda: init_road_state(T))

            for r, ts, speed, signed_d, direction in rows:

                state = D[r]

                # ---- global min/max ----
                state["v_min"] = min(state["v_min"], speed)
                state["v_max"] = max(state["v_max"], speed)

                state["d_left"] = min(state["d_left"], signed_d)
                state["d_right"] = max(state["d_right"], signed_d)

                # ---- signed distance stats (Welford) ----
                state["n_d"] += 1
                delta = signed_d - state["mu_d"]
                state["mu_d"] += delta / state["n_d"]
                delta2 = signed_d - state["mu_d"]
                state["M_d"] += delta * delta2

                # ---- direction counts ----
                res = r * direction
                if res > 0:
                    state["n_forward"] += 1
                if res < 0:
                    state["n_backward"] += 1

                # ---- time-binned speed stats ----
                t = time_bin(ts, T)
                vstate = state["v"][t]

                vstate["n"] += 1
                delta = speed - vstate["mu"]
                vstate["mu"] += delta / vstate["n"]
                delta2 = speed - vstate["mu"]
                vstate["M"] += delta * delta2

            # ---- batch DB updates ----
            update_metadata_table(conn, D)
            update_temp_table(conn, D)

    # ---- final post-processing ----
    with conn.cursor() as cur:
        cur.execute("SELECT update_road_type()")
        cur.execute("SELECT update_width_attributes()")
        cur.execute("SELECT update_oneway_attribute()")
    conn.commit()