# Multi-Agent Adaptive Control with Control-Barrier-Function Safety Filters

A four-agent simulation in 2-D that reproduces the architecture of
Solano-Castellanos, Fisher, and Annaswamy
([arXiv 2403.15674, MECC 2025](https://arxiv.org/abs/2403.15674)):
distributed adaptive control under unknown gain, with a Zeroing
Control Barrier Function (ZCBF) safety filter enforcing inter-agent
collision avoidance.

This is a direct continuation of the single-agent Dubins adaptive
control work in [Maldonado-Naranjo & Annaswamy, IEEE L-CSS 2025](https://ieeexplore.ieee.org/abstract/document/11045800)
extended to a multi-agent setting with collision avoidance.

## Architecture

For each agent *i*:

```
Plant:           ẋ_i      =  Λ_i  u_i               (Λ_i unknown, sign known)
Reference:       ż_i      =  u_i_ref                (driven by formation law)
Adaptive law:    θ̂̇_i      =  −γ / (1 + ‖u_ref‖²)  ·  u_i_ref^T (x_i − z_i)
Adaptive ctrl:   u_i      =  θ̂_i  u_i_ref            (θ̂_i  ≈  1 / Λ_i)
Safety filter:   u_i^safe =  argmin_u  ‖u − u_i‖²  s.t. inter-agent ZCBFs
```

The reference law is distributed (each agent sees only its own state and
its neighbours' states):

```
u_i_ref  =  −K_target (z_i − t_i)
            −K_form  Σ_{j ∈ N_i}  [ (z_i − z_j)  −  (t_i − t_j) ]
```

Inter-agent ZCBFs (one per pair `(i, j)` with `i ≠ j` in the safety
filter for agent *i*):

```
h_ij(x)        =  ‖x_i − x_j‖²  −  r_safe²       (≥ 0  =  safe)
constraint:      d/dt h_ij  +  α h_ij  ≥  0
```

Per-agent QP (solved with `cvxpy` / OSQP):

```
min_{u}    ‖u − u_nom_i‖²
s.t.       2 (x_i − x_j)^T u  −  2 (x_i − x_j)^T u_nom_j  +  α h_ij(x)  ≥  0
           for every neighbour j of i
           ‖u‖_∞  ≤  1.5  u_max
```

## Run

```bash
python multi_agent_cbf.py
```

Outputs (in `./output/`):

- `01_four_conditions.png` – cross-swap formation under four conditions
  (nominal, uncertain plant alone, +AC, +AC+CBF)
- `02_full_system.png` – headline trajectory under AC + CBF
- `03_adaptation.png` – `θ̂_i` convergence vs `1/Λ_i`, plus per-agent
  target-tracking error
- `04_safety.png` – minimum pairwise inter-agent distance over time
  for all four conditions, with the safety threshold `r_safe = 0.40`
  drawn as a dashed line

## Headline Results

Cross-swap formation. Each agent at a corner of a 6×6 square heads to
the diagonally-opposite corner. True gains
`Λ = [0.6, 1.4, 0.9, 1.6]`, ideal estimates `1/Λ = [1.67, 0.71, 1.11, 0.63]`.

| Scenario | Min sep | Mean tracking err | Notes |
|---|---:|---:|---|
| 1. Nominal (Λ = 1) | 0.010 | small | Cross-swap forces collisions through centre |
| 2. Uncertain plant, no AC, no CBF | 0.010 | 3.18 | Plant lags, agents drift, collisions |
| 3. Uncertain plant + AC | **0.028** | **0.74** | AC recovers tracking but no safety |
| 4. Uncertain plant + AC + CBF | **0.388** | 0.96 | CBF tightens to ≈ `r_safe = 0.40` |

The CBF cuts collision risk by ≈ 14× (min sep 0.028 → 0.388). The
remaining 0.012 gap to `r_safe = 0.40` is from the forward-Euler
discretisation of a continuous-time barrier constraint plus the
distributed approximation in the safety filter (each agent assumes
its neighbours apply their nominal commands while solving its own
QP, and the four agents resolve simultaneously).

## Where this builds on existing work

- **Single-agent precursor:** [Maldonado-Naranjo & Annaswamy, "Adaptive
  Control for Dubins Vehicle Path Following", IEEE Control Systems Letters, 2025](https://ieeexplore.ieee.org/abstract/document/11045800).
- **Multi-agent foundation:** [Solano-Castellanos, Fisher & Annaswamy,
  "Safe and Stable Formation Control with Distributed Multi-Agents
  Using Adaptive Control and Control Barrier Functions", arXiv
  2403.15674, MECC 2025](https://arxiv.org/abs/2403.15674).
- **CBF theory:** Ames, Coogan, Egerstedt, Notomista, Sreenath, Tabuada,
  "Control Barrier Functions: Theory and Applications", ECC 2019.

## Files

```
Multi-Agent-CBF/
├── multi_agent_cbf.py     # full simulation + figure generation
├── README.md              # this file
└── output/
    ├── 01_four_conditions.png
    ├── 02_full_system.png
    ├── 03_adaptation.png
    └── 04_safety.png
```
