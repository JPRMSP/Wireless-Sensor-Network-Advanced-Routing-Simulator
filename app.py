import streamlit as st
import math
import random
import numpy as np
import matplotlib.pyplot as plt

WIDTH, HEIGHT = 100, 100
INITIAL_ENERGY = 1.0
TX_COST = 0.02
RX_COST = 0.01
BS_POS = (50, 115)


def distance(a, b):
    return math.dist(a, b)


def create_nodes(n):
    return [
        {
            "id": i,
            "pos": (random.randint(0, WIDTH), random.randint(0, HEIGHT)),
            "energy": INITIAL_ENERGY,
            "alive": True
        }
        for i in range(n)
    ]


def use_energy(node, amount):
    if node["alive"]:
        node["energy"] -= amount
        if node["energy"] <= 0:
            node["alive"] = False


# ------------------- ROUTING -------------------

def direct_routing(nodes, packets):
    paths, delivered = [], 0
    for n in nodes:
        if not n["alive"]:
            continue
        d = distance(n["pos"], BS_POS)
        use_energy(n, TX_COST * (d / 50))
        if n["alive"]:
            delivered += packets
            paths.append((n["pos"], BS_POS))
    return nodes, paths, delivered


def leach(nodes, packets):
    alive_nodes = [n for n in nodes if n["alive"]]
    if not alive_nodes:
        return nodes, [], 0

    num_ch = max(1, len(alive_nodes) // 10)
    cluster_heads = random.sample(alive_nodes, num_ch)

    paths, delivered = [], 0

    for n in alive_nodes:
        if n in cluster_heads:
            d = distance(n["pos"], BS_POS)
            use_energy(n, TX_COST * (d / 60))
            delivered += packets
            paths.append((n["pos"], BS_POS))
        else:
            ch = min(cluster_heads, key=lambda c: distance(c["pos"], n["pos"]))
            d = distance(n["pos"], ch["pos"])
            use_energy(n, TX_COST * (d / 60))
            use_energy(ch, RX_COST * 0.4)
            paths.append((n["pos"], ch["pos"]))
    return nodes, paths, delivered


def pegasis(nodes, packets):
    alive_nodes = sorted([n for n in nodes if n["alive"]], key=lambda x: x["pos"][0])
    paths, delivered = [], 0

    for i in range(len(alive_nodes) - 1):
        a, b = alive_nodes[i], alive_nodes[i + 1]
        d = distance(a["pos"], b["pos"])
        use_energy(a, TX_COST * (d / 70))
        use_energy(b, RX_COST * 0.4)
        paths.append((a["pos"], b["pos"]))

    if alive_nodes:
        last = alive_nodes[-1]
        d = distance(last["pos"], BS_POS)
        use_energy(last, TX_COST * (d / 60))
        delivered += packets
        paths.append((last["pos"], BS_POS))

    return nodes, paths, delivered


def teen(nodes, packets, hard_th, soft_th):
    """
    TEEN: nodes transmit only when sensed value crosses threshold
    We simulate sensed values randomly.
    """
    paths, delivered = [], 0

    for n in nodes:
        if not n["alive"]:
            continue

        sensed = random.uniform(0, 100)

        if sensed >= hard_th and sensed - soft_th >= 0:
            d = distance(n["pos"], BS_POS)
            use_energy(n, TX_COST * (d / 55))
            if n["alive"]:
                delivered += packets
                paths.append((n["pos"], BS_POS))

    return nodes, paths, delivered


# ------------------- VISUAL -------------------

def draw(nodes, paths, title):
    fig, ax = plt.subplots()

    alive = [n for n in nodes if n["alive"]]
    dead = [n for n in nodes if not n["alive"]]

    if alive:
        ax.scatter([n["pos"][0] for n in alive], [n["pos"][1] for n in alive], s=40, label="Alive")
    if dead:
        ax.scatter([n["pos"][0] for n in dead], [n["pos"][1] for n in dead], s=40, color="red", label="Dead")

    for p in paths:
        ax.plot([p[0][0], p[1][0]], [p[0][1], p[1][1]])

    ax.scatter(BS_POS[0], BS_POS[1], marker="s", s=80, label="Base Station")
    ax.set_title(title)
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, 120)
    ax.legend()
    st.pyplot(fig)


# ------------------- APP -------------------

st.title("Wireless Sensor Network — Advanced Routing Simulator")
st.caption("No datasets • No ML • Pure routing theory in action")

num_nodes = st.slider("Nodes", 10, 150, 50)
rounds = st.slider("Simulation rounds", 5, 80, 20)
packets = st.slider("Packets generated per round", 1, 10, 3)

mode = st.radio(
    "Mode",
    ["Single Protocol", "Compare Protocols"]
)

protocols = ["Direct", "LEACH", "PEGASIS", "TEEN"]

if mode == "Single Protocol":
    proto = st.selectbox("Routing Protocol", protocols)

    hard = st.slider("TEEN Hard Threshold", 10, 90, 50) if proto == "TEEN" else None
    soft = st.slider("TEEN Soft Threshold", 1, 20, 5) if proto == "TEEN" else None

    if st.button("Simulate"):
        nodes = create_nodes(num_nodes)
        dead_history, energy_history = [], []
        delivered_total = 0

        for r in range(rounds):
            if proto == "Direct":
                nodes, paths, delivered = direct_routing(nodes, packets)
            elif proto == "LEACH":
                nodes, paths, delivered = leach(nodes, packets)
            elif proto == "PEGASIS":
                nodes, paths, delivered = pegasis(nodes, packets)
            else:
                nodes, paths, delivered = teen(nodes, packets, hard, soft)

            delivered_total += delivered
            dead_history.append(sum(not n["alive"] for n in nodes))
            energy_history.append(sum(max(n["energy"], 0) for n in nodes))

        draw(nodes, paths, f"Final State — {proto}")
        st.subheader("Metrics")
        st.write(f"Packets delivered: **{delivered_total}**")
        st.write(f"Dead nodes: **{dead_history[-1]} / {num_nodes}**")

        st.line_chart(dead_history, height=200)
        st.line_chart(energy_history, height=200)

else:
    if st.button("Run Comparison"):
        results = {}
        for proto in protocols[:3]:  # avoid TEEN for fairness
            nodes = create_nodes(num_nodes)
            delivered = 0

            for _ in range(rounds):
                if proto == "Direct":
                    nodes, _, d = direct_routing(nodes, packets)
                elif proto == "LEACH":
                    nodes, _, d = leach(nodes, packets)
                else:
                    nodes, _, d = pegasis(nodes, packets)
                delivered += d

            results[proto] = {
                "alive": sum(n["alive"] for n in nodes),
                "delivered": delivered
            }

        st.subheader("Protocol Comparison")
        st.table(results)
