# SpendGuard Engine

Open-source shared engine for SpendGuard wrappers.

Contains:
- Provider adapters (`spendguard_engine.providers`)
- Billing math (`spendguard_engine.billing`)
- Pricing types/defaults (`spendguard_engine.pricing`)
- Shared schemas (`spendguard_engine.schemas`)

Wrapper services (`spendguard-sidecar`, `spendguard-cloud`) should own pricing-source fetching,
auth, storage, and commercial concerns.

## License

MIT. See `LICENSE`.
