# Full metric inventory (verification plan §13)

Canonical policy context: [VERIFICATION_MASTER_SPEC.md](VERIFICATION_MASTER_SPEC.md). Repository index: [README.md](../README.md) (*Documentation map*). This file lists metrics the team should **record or roadmap** when stress-testing Moreau through the repository. Not all are implemented in scripts today; see `output/` artifacts and `scripts/` for what is currently emitted.

## 13.1 Environment and install metrics

- diagnostics pass/fail  
- visible devices  
- default device  
- optional dependency presence  
- license availability  
- import success rate  
- bootstrap time  
- package/version fingerprint  
- environment drift across machines  

## 13.2 Core solver metrics

- solver status  
- objective value  
- solve time  
- setup time  
- construction time  
- iterations  
- primal solution norm  
- slack norm  
- dual norm  
- infeasible, failed, or error rate  

## 13.3 Reference correctness metrics

- objective delta vs reference  
- primal infinity-norm delta vs reference  
- primal L2 delta vs reference  
- status agreement rate  
- max feasibility residual  
- average feasibility residual  
- tolerance violation count  
- pass rate by family  
- pass rate by size  
- pass rate by density  
- pass rate by conditioning bucket  

## 13.4 Native parity metrics

- action match rate  
- active-constraint match rate  
- proposed distribution Linf delta  
- proposed distribution L2 delta  
- corrected distribution Linf delta  
- corrected distribution L2 delta  
- intervention norm absolute difference  
- objective absolute difference  
- solver-status mismatch count  
- parity failure count by scenario  
- parity failure count by step  
- parity failure localization by arm  

## 13.5 Warm-start metrics

- cold iterations vs warm iterations  
- cold solve time vs warm solve time  
- iteration reduction ratio  
- warm-start speedup ratio  
- warm-start success rate  
- warm-start degradation cases  
- benefit vs problem drift magnitude  
- benefit vs sequence length  

## 13.6 Batching metrics

- batch solve time  
- average solve time per item  
- throughput in problems per second  
- speedup vs sequential loop  
- batch efficiency ratio  
- memory growth vs batch size  
- batch status heterogeneity  
- variance across items in batch  
- maximum batch size before degradation  

## 13.7 Device-selection metrics

- chosen device per run  
- forced device vs auto device  
- CPU p50/p95/p99  
- CUDA p50/p95/p99  
- setup overhead by device  
- crossover size for CUDA win  
- crossover density for CUDA win  
- crossover batch size for CUDA win  
- wrong-device selection count in auto mode  
- autotune first-solve cost  
- autotune steady-state gain  

## 13.8 Problem-structure metrics

- dimension n  
- dimension m  
- ratio m/n  
- matrix density  
- sparsity complexity  
- cone composition  
- number of zero-cone rows  
- number of nonnegative-cone rows  
- number and size of SOC blocks  
- scaling severity proxy  
- repeated-structure reuse depth  

## 13.9 Differentiation metrics

- gradient finite-rate  
- NaN rate  
- inf rate  
- finite-difference mismatch  
- backward latency  
- gradient norm statistics  
- gradient stability near active-set changes  
- framework-specific mismatch  
- batch gradient throughput  
- memory during backward  

## 13.10 Smoothed-differentiation metrics

- gradient smoothness proxy  
- gradient variance  
- finite-difference mismatch  
- solution drift from exact solve  
- objective drift from exact solve  
- smoothing vs stability tradeoff  

## 13.11 PyTorch metrics

- autograd success rate  
- backward latency  
- device transfer overhead  
- gradient agreement with native path  
- batch throughput  
- device-consistency errors  

## 13.12 JAX metrics

- grad success rate  
- vmap throughput  
- jit compile cost  
- jit steady-state latency  
- warm-start API path behavior  
- device-consistency behavior  

## 13.13 CVXPY and cvxpylayers metrics

- CVXPY compile time  
- CVXPY solve time with Moreau  
- model-to-solver reformulation overhead  
- cvxpylayers forward latency  
- cvxpylayers backward latency  
- parameter-batch throughput  
- correctness delta between high-level and native paths  

## 13.14 Testing-utility coverage metrics

- random feasible problems generated  
- family coverage across cone types  
- failure rate on random feasible instances  
- failure clustering by size, device, cone type, or batch size  
- reproducibility across seeds  

## 13.15 Governance metrics

- artifact gate  
- fixture gate  
- parity gate  
- promotion gate  
- review-lock  
- audit error count  
- audit warning count  
- native endorsement status  
- number of active families  
- number of published runs  
- number of candidate runs  
- family-bump count  
