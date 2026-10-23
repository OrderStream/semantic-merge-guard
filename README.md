# semantic-merge-guard 🔀🛑

[![GitHub Action](https://img.shields.io/badge/GitHub%20Action-v1.0.0-orange?logo=githubactions)](https://github.com/OrderStream/semantic-merge-guard)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-Passing-brightgreen.svg)]()
[![OrderStream Polar](https://img.shields.io/badge/Polar-OrderStream-blue.svg)](https://polar.sh/orderstream)
[![Stellar XLM/USDC](https://img.shields.io/badge/Stellar-USDC%2FXLM-black.svg)](#direct-web3-wallet-monetization)
[![Base USDC](https://img.shields.io/badge/Base-USDC-0052FF.svg)](#direct-web3-wallet-monetization)

Cross-file AST dependency graph analyzer in CI that catches silent semantic merge conflicts that text-based Git merges miss.

---

## 💥 The Friction & Dollar Cost
Git is purely text-based (lines of characters). When two developers merge separate branches:
- **Developer A** updates `calculateBilling(account, rate, region)` to require a mandatory 3rd argument `region`.
- **Developer B** in a separate branch calls `calculateBilling(account, rate)` in `invoice.ts`.
- **Git** auto-merges cleanly with 0 text conflicts because both developers touched different files.
- The build lands in `main`, and production crashes with `TypeError: calculateBilling requires 3 arguments`.

**semantic-merge-guard** runs during Pull Requests, maps cross-file AST dependencies, identifies arity changes, duplicate endpoint definitions, and deleted contracts, and blocks the merge before shipping.

---

## 🚀 Quick Start

### Installation
```bash
pip install semantic-merge-guard
```

### CLI Usage
```bash
# Scan repository for cross-file AST semantic conflicts
semantic-merge-guard check --path .

# Enforce strict zero-warning policy
semantic-merge-guard check --path . --fail-on-warning

# Check license & zero-fee wallet payment details
semantic-merge-guard license
```

---

## 🤖 GitHub Action Integration

```yaml
- name: Semantic Merge Guard CI
  uses: OrderStream/semantic-merge-guard@v1
  with:
    path: "."
    fail_on_warning: false
```

---

---

## 💳 Enterprise Pricing Matrix & Licensing

| Tier | Price | Repositories | Core Capabilities |
| :--- | :--- | :--- | :--- |
| **Community Free** | **** | Unlimited | Standalone CLI runner and single-repo GitHub Action |
| **Starter Suite** | ** / mo** | Up to 10 Repos | Automated CI PR gates, 500 CI runs/mo, standard email support |
| **Team Platform** | **,499 / mo** | Up to 50 Repos | Full 10-tool OrderStream suite, flaky test quarantine deterministic replay, zero-downtime shadow DB migration guard, 24/7 telemetry alarms |
| **Enterprise Platform** | **,999 / mo** | Unlimited | Multi-repo speculative merge engine, zero-downtime migration orchestrator, WASM sandbox gate, dedicated 24/7 cloud keeper, custom SLA |
| **M&A IP & Security Audit** | **,000 one-time** | Whole Organization | Comprehensive copyleft AST fuzzy fingerprint audit, snippet license sheriff certification, formal invariant verification, and executive forensic IP Cleanliness Certificate |

## 💰 Direct Web3 Wallet Monetization & Polar Integration

Support this project or purchase enterprise AST monorepo indexing with **0 platform fees**:

- **Polar Subscription & Sponsorship:** [https://polar.sh/orderstream](https://polar.sh/orderstream)
- **Stellar Network (Native XLM / USDC):**
  - Public Key: `GABFQIK63R2NETJM7T673EAMZN4RJLLGP3OFUEJU5ZVTGWUKULZJNL6`
  - Memo (Required): `400566831`
- **EVM (Base / Arbitrum / Ethereum USDT & USDC):**
  - Address: `0x5de2b62434754bfd39ef350a3a867ed3eced5074`
