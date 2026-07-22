# S8 decision-grade benchmark report

Generated: `2026-07-22T23:36:44Z`
Commit: `d7f1da49b893557dd72e5d55fbc6018d79eb255e`
Host: `{'system': 'Windows', 'release': '11', 'machine': 'AMD64', 'python': '3.12.10', 'executable': 'C:\\Users\\mateo\\AppData\\Local\\Programs\\Python\\Python312\\python.exe'}`

## Counts

- total cells: 40
- ok: 31
- fail: 0
- NOT_RUN: 9

## Backend comparisons

| label | status | p50 e2e (s) | p95 | p99 | max | reason |
|-------|--------|-------------|-----|-----|-----|--------|
| public_reference | ok | 0.008724450002773665 | 0.009736594994319602 | 0.009844678993104025 | 0.009871699992800131 |  |
| public_scs | ok | 0.008359250001376495 | 0.009665785001561743 | 0.00969075700137182 | 0.00969700000132434 |  |
| moreau_cvxpy | NOT_RUN |  |  |  |  | ImportError: 
The 'moreau' package cannot be installed directly from PyPI.
Moreau is not supported on Windows. Please use WSL (Windows Subsystem for Linux).
Please visit https://docs.moreau.so for installation instructions.
 |
| moreau_native | NOT_RUN |  |  |  |  | ImportError: 
The 'moreau' package cannot be installed directly from PyPI.
Moreau is not supported on Windows. Please use WSL (Windows Subsystem for Linux).
Please visit https://docs.moreau.so for installation instructions.
 |
| heterogeneous_batch | NOT_RUN |  |  |  |  | Native heterogeneous batch requires licensed Moreau; not runnable on native Windows host |
| windows_sidecar | NOT_RUN |  |  |  |  | WSL Moreau sidecar scaffolding present; live licensed Moreau worker not attested on this host (declared qualification: protocol/tests + public CI, not production-ready live Moreau) |

## Claim guardrails

- Do not publish vendor Moreau latency from this report unless status=ok on moreau_* comparisons.
- Do not claim native Windows Moreau support.
- Public Clarabel/SCS numbers are host-specific; label environment provenance when citing.
- Sidecar remains qualification scaffolding until live Moreau worker attestation exists.

## Cells

### `cold_n4_well_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.011379399998986628 / 0.013111630000639706 / 0.013214566002134234 / 0.013240300002507865
- stderr(mean): 0.0009144706930682716
- solver p50: 0.0001075
- verification p50 (est.): 0.011235999998986628

### `cold_n4_well_public_scs` (ok)
- e2e p50/p95/p99/max: 0.010425500004203059 / 0.018661089990200705 / 0.01981469798905891 / 0.020103099988773465
- stderr(mean): 0.0026264293064328253
- solver p50: 3.15e-05
- verification p50 (est.): 0.010332700004203058

### `cold_n4_well_auto` (ok)
- e2e p50/p95/p99/max: 0.01306664999719942 / 0.01568647499589133 / 0.01590121499481029 / 0.01595489999454003
- stderr(mean): 0.0014734450770937922
- solver p50: 0.00012989999999999999
- verification p50 (est.): 0.012915399997199421

### `cold_n4_ill_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.012015249994874466 / 0.05836621499329338 / 0.06480660299246664 / 0.06641669999225996
- stderr(mean): 0.013768916890785311
- solver p50: 9.335e-05
- verification p50 (est.): 0.011924499994874466

### `cold_n4_ill_public_scs` (ok)
- e2e p50/p95/p99/max: 0.01372195000294596 / 0.014244265011802782 / 0.014290693012590054 / 0.014302300012786873
- stderr(mean): 0.0005803500098409131
- solver p50: 0.00016995
- verification p50 (est.): 0.013485300002945958
- failures: ['VerificationReleaseError: no verified action could be released after fallback ladder', 'VerificationReleaseError: no verified action could be released after fallback ladder']

### `cold_n4_ill_auto` (ok)
- e2e p50/p95/p99/max: 0.011620549994404428 / 0.014077380001253914 / 0.014376996002101804 / 0.014451900002313778
- stderr(mean): 0.0013325292104616083
- solver p50: 0.00011515
- verification p50 (est.): 0.011504599994404428

### `cold_n8_well_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.011127700003271457 / 0.011464064991014312 / 0.011475452988670441 / 0.011478299988084473
- stderr(mean): 0.0006991358033297815
- solver p50: 0.00015815000000000002
- verification p50 (est.): 0.010818750003271458

### `cold_n8_well_public_scs` (ok)
- e2e p50/p95/p99/max: 0.010672650001652073 / 0.01461011000428698 / 0.015084662004810524 / 0.015203300004941411
- stderr(mean): 0.0013745210186890833
- solver p50: 5.6649999999999995e-05
- verification p50 (est.): 0.010496250001652073

### `cold_n8_well_auto` (ok)
- e2e p50/p95/p99/max: 0.012295649998122826 / 0.013851694996992592 / 0.014011858997691888 / 0.014051899997866713
- stderr(mean): 0.0009797919257092712
- solver p50: 0.000192
- verification p50 (est.): 0.012103649998122825

### `cold_n8_ill_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.011623250007687602 / 0.016609264998260185 / 0.017108812997030327 / 0.017233699996722862
- stderr(mean): 0.0017636618342394736
- solver p50: 0.00014330000000000001
- verification p50 (est.): 0.011425200007687602

### `cold_n8_ill_public_scs` (ok)
- e2e p50/p95/p99/max: 0.009914399997796863 / 0.009988830001384485 / 0.009995446001703386 / 0.00999710000178311
- stderr(mean): 8.270000398624688e-05
- solver p50: 0.00023100000000000003
- verification p50 (est.): 0.009623199997796863
- failures: ['VerificationReleaseError: no verified action could be released after fallback ladder', 'VerificationReleaseError: no verified action could be released after fallback ladder']

### `cold_n8_ill_auto` (ok)
- e2e p50/p95/p99/max: 0.011002650004229508 / 0.015056395008286925 / 0.015614719009317922 / 0.015754300009575672
- stderr(mean): 0.0015508632871103845
- solver p50: 0.00020175
- verification p50 (est.): 0.010822750004229508

### `constraint_kinds_matrix` (ok)

### `warm_seq_n4_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.008724450002773665 / 0.009736594994319602 / 0.009844678993104025 / 0.009871699992800131
- stderr(mean): 0.00045550538390352484
- solver p50: 9.15e-05
- verification p50 (est.): 0.008614100002773665

### `episode_reset_n4_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.009759499997016974 / 0.012144689999695401 / 0.01245541800133651 / 0.012533100001746789
- stderr(mean): 0.0009064794565864963
- solver p50: 0.00011705
- verification p50 (est.): 0.009620449997016974

### `warm_seq_n8_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.011926049999601673 / 0.012320845002977875 / 0.01234864900339744 / 0.012355600003502332
- stderr(mean): 0.0005523091503674857
- solver p50: 0.0001677
- verification p50 (est.): 0.011762649999601672

### `episode_reset_n8_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.009614850001526065 / 0.010766210004658204 / 0.010836122004402569 / 0.01085360000433866
- stderr(mean): 0.0005869857731086095
- solver p50: 0.00013475
- verification p50 (est.): 0.009456650001526064

### `microbatch_n4_bs1_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.00993035000283271 / 0.01026771500473842 / 0.010297703004907817 / 0.010305200004950166
- stderr(mean): 0.000374850002117455
- solver p50: 0.00011585
- verification p50 (est.): 0.00981450000283271

### `microbatch_n4_bs4_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.04629595000005793 / 0.050750544999027626 / 0.051146508998936045 / 0.05124549999891315
- stderr(mean): 0.004949549998855217
- solver p50: 0.00010834999999999999
- verification p50 (est.): 0.04618760000005793

### `microbatch_n4_bs8_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.07779645000118762 / 0.08417137499345699 / 0.08473803499276983 / 0.08487969999259803
- stderr(mean): 0.007083249991410412
- solver p50: 9.620000000000001e-05
- verification p50 (est.): 0.07770025000118763

### `microbatch_n8_bs1_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.009793749995878898 / 0.010997724995831959 / 0.011104744995827786 / 0.011131499995826744
- stderr(mean): 0.001337749999947846
- solver p50: 0.00016395
- verification p50 (est.): 0.009629799995878898

### `microbatch_n8_bs4_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.04619934999936959 / 0.04745300500435405 / 0.04756444100479712 / 0.047592300004907884
- stderr(mean): 0.001392950005538296
- solver p50: 0.00018449999999999999
- verification p50 (est.): 0.04601484999936959

### `microbatch_n8_bs8_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.07605360000161454 / 0.0784371599991573 / 0.07864903199893888 / 0.07870199999888428
- stderr(mean): 0.0026483999972697343
- solver p50: 0.00013955
- verification p50 (est.): 0.07591405000161454

### `native_structural_cache_hit_miss` (NOT_RUN)
- reason: Native structural fingerprint cache requires Moreau compiled path; not available on this host

### `cold_n4_nominal_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.008474750000459608 / 0.01087276000107522 / 0.011140072002162923 / 0.01120690000243485
- stderr(mean): 0.0007699033774088403
- solver p50: 9.355e-05
- verification p50 (est.): 0.008375750000459608

### `cold_n4_nominal_public_scs` (ok)
- e2e p50/p95/p99/max: 0.008359250001376495 / 0.009665785001561743 / 0.00969075700137182 / 0.00969700000132434
- stderr(mean): 0.0006983563622874922
- solver p50: 2.42e-05
- verification p50 (est.): 0.008290650001376495

### `cold_n4_nominal_auto` (ok)
- e2e p50/p95/p99/max: 0.009346800005005207 / 0.009629344991844846 / 0.00966242899055942 / 0.009670699990238063
- stderr(mean): 0.00026429921895469185
- solver p50: 9.730000000000001e-05
- verification p50 (est.): 0.009249500005005207

### `compare_cvxpy_moreau` (NOT_RUN)
- reason: ImportError: 
The 'moreau' package cannot be installed directly from PyPI.
Moreau is not supported on Windows. Please use WSL (Windows Subsystem for Linux).
Please visit https://docs.moreau.so for installation instructions.


### `compare_native_moreau` (NOT_RUN)
- reason: ImportError: 
The 'moreau' package cannot be installed directly from PyPI.
Moreau is not supported on Windows. Please use WSL (Windows Subsystem for Linux).
Please visit https://docs.moreau.so for installation instructions.


### `native_heterogeneous_batch` (NOT_RUN)
- reason: Native heterogeneous batch requires licensed Moreau; not runnable on native Windows host

### `native_cpu_algo_choices` (NOT_RUN)
- reason: Native Moreau CPU algorithm knobs not exposed/available on this host

### `native_auto_device` (NOT_RUN)
- reason: Native auto device selection requires Moreau

### `cuda_native` (NOT_RUN)
- reason: CUDA probe failed: 
The 'moreau' package cannot be installed directly from PyPI.
Moreau is not supported on Windows. Please use WSL (Windows Subsystem for Linux).
Please visit https://docs.moreau.so for installation instructions.


### `sidecar_ipc_overhead` (NOT_RUN)
- reason: WSL Moreau sidecar scaffolding present; live licensed Moreau worker not attested on this host (declared qualification: protocol/tests + public CI, not production-ready live Moreau)

### `sidecar_worker_restart` (NOT_RUN)
- reason: WSL Moreau sidecar scaffolding present; live licensed Moreau worker not attested on this host (declared qualification: protocol/tests + public CI, not production-ready live Moreau)

### `concurrent_n4_w4_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.016872799998964183 / 0.03125495999556733 / 0.03313891199737554 / 0.0336098999978276
- stderr(mean): 0.002650411983703886

### `max_iter1_n4_public_clarabel` (ok)

### `infeasible_empty_allowed_n4_public_clarabel` (ok)

### `ill_conditioned_n4_public_clarabel` (ok)
- e2e p50/p95/p99/max: 0.009783400004380383 / 0.014476980007020756 / 0.0149513160076458 / 0.015069900007802062
- stderr(mean): 0.0017221740902938934
- solver p50: 0.0001127
- verification p50 (est.): 0.009670700004380382

### `nan_proposal_public_clarabel` (ok)

