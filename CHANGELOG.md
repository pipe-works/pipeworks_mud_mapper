# Changelog

## [0.0.10](https://github.com/pipe-works/pipeworks_mud_mapper/compare/pipeworks-mud-mapper-v0.0.9...pipeworks-mud-mapper-v0.0.10) (2026-02-02)


### Features

* add validation UI with report generation ([ccea6b9](https://github.com/pipe-works/pipeworks_mud_mapper/commit/ccea6b9136865f964997fd571b3f250564b0a80b))

## [0.0.9](https://github.com/pipe-works/pipeworks_mud_mapper/compare/pipeworks-mud-mapper-v0.0.8...pipeworks-mud-mapper-v0.0.9) (2026-02-02)


### Features

* add delete room functionality with undo ([3be6176](https://github.com/pipe-works/pipeworks_mud_mapper/commit/3be6176b66a1a0ee7faef57f00658ce13636f204))


### Documentation

* update documentation for v0.0.8 changes ([ec3d218](https://github.com/pipe-works/pipeworks_mud_mapper/commit/ec3d218b244a560c8076b3f24b465efe888b2e35))

## [0.0.8](https://github.com/pipe-works/pipeworks_mud_mapper/compare/pipeworks-mud-mapper-v0.0.7...pipeworks-mud-mapper-v0.0.8) (2026-02-02)


### Features

* add JSON Schema for map files ([ca61c7b](https://github.com/pipe-works/pipeworks_mud_mapper/commit/ca61c7b46e172238a2387d985fe324c828f148d7))


### Fixes

* enable save button when sending LLM text to room description ([d5b09fe](https://github.com/pipe-works/pipeworks_mud_mapper/commit/d5b09fe9fda62ee551b579110db4b4d0caad7167))
* prevent has_unsaved reset when file list re-renders ([5fa7acb](https://github.com/pipe-works/pipeworks_mud_mapper/commit/5fa7acb9e93471369cddaaac187677fee839fd31))
* resolve save/export button disappearing in flexbox layout ([4dd66d2](https://github.com/pipe-works/pipeworks_mud_mapper/commit/4dd66d20e721f8abedd0c41b0acd631f89859bd9))

## [0.0.7](https://github.com/pipe-works/pipeworks_mud_mapper/compare/pipeworks-mud-mapper-v0.0.6...pipeworks-mud-mapper-v0.0.7) (2026-02-02)


### Features

* add Ollama LLM integration for room descriptions ([#8](https://github.com/pipe-works/pipeworks_mud_mapper/issues/8)) ([35a37a0](https://github.com/pipe-works/pipeworks_mud_mapper/commit/35a37a08c2fef5ab28cda9b3b916e1071c940420))

## [0.0.6](https://github.com/pipe-works/pipeworks_mud_mapper/compare/pipeworks-mud-mapper-v0.0.5...pipeworks-mud-mapper-v0.0.6) (2026-02-02)


### Documentation

* improve README with badges and cleaner structure ([5028a13](https://github.com/pipe-works/pipeworks_mud_mapper/commit/5028a13e59c13a4c6cc44a19ea3ee7f1874ba76d))

## [0.0.5](https://github.com/pipe-works/pipeworks_mud_mapper/compare/pipeworks-mud-mapper-v0.0.4...pipeworks-mud-mapper-v0.0.5) (2026-02-02)


### Features

* implement two-file workflow (Phase 5) ([6b39800](https://github.com/pipe-works/pipeworks_mud_mapper/commit/6b398008af020d90ab58a51153fe7de1dc820621))
* **models:** add Pydantic domain models for two-file workflow ([911a9f4](https://github.com/pipe-works/pipeworks_mud_mapper/commit/911a9f44b5ee1b4063c6d7921cb588ef1dd5ed1c))
* **services:** add service layer for business logic ([605ba39](https://github.com/pipe-works/pipeworks_mud_mapper/commit/605ba3933f4c5db6a42ef5d703e4936ce6be447a))


### Documentation

* update documentation for two-file workflow and architecture ([5d5cfbd](https://github.com/pipe-works/pipeworks_mud_mapper/commit/5d5cfbd2d0e5fe1a5d040d2f3e47550606c8117a))


### Internal Changes

* extract callbacks from app.py (Phase 4) ([52e3ef9](https://github.com/pipe-works/pipeworks_mud_mapper/commit/52e3ef95dd628080832c61173352769d393a4d6b))
* extract layout components from app.py (Phase 3) ([ac30b96](https://github.com/pipe-works/pipeworks_mud_mapper/commit/ac30b961e110e72918c3c4923818bc6f5dc7f03c))

## [0.0.4](https://github.com/pipe-works/pipeworks_mud_mapper/compare/pipeworks-mud-mapper-v0.0.3...pipeworks-mud-mapper-v0.0.4) (2026-02-02)


### Features

* add exit management and Sphinx documentation ([98da84b](https://github.com/pipe-works/pipeworks_mud_mapper/commit/98da84b89f884265c9130d065e7485e6d881b3f5))


### Fixes

* remove Python 3.11 compat code and enable docs CI ([6f873a2](https://github.com/pipe-works/pipeworks_mud_mapper/commit/6f873a2a1940135991f37e8f9bf645cc63a7a972))

## [0.0.3](https://github.com/pipe-works/pipeworks_mud_mapper/compare/pipeworks-mud-mapper-v0.0.2...pipeworks-mud-mapper-v0.0.3) (2026-02-01)


### Features

* add room selection, editing, and save functionality ([3bb3dc1](https://github.com/pipe-works/pipeworks_mud_mapper/commit/3bb3dc133d4374619d6e711ae68ddf82fbc8eccd))

## [0.0.2](https://github.com/pipe-works/pipeworks_mud_mapper/compare/pipeworks-mud-mapper-v0.0.1...pipeworks-mud-mapper-v0.0.2) (2026-02-01)


### Features

* add Dash-based mapper UI skeleton ([f8386ac](https://github.com/pipe-works/pipeworks_mud_mapper/commit/f8386acf5234f3b2488fc21f6aee229c01d7bfda))
* add zone creation, loading, and map visualization ([f9f56c6](https://github.com/pipe-works/pipeworks_mud_mapper/commit/f9f56c60a794f7137196ac1d975afe7c11e5507a))
* initialize pipeworks_mud_mapper repository ([4e0d723](https://github.com/pipe-works/pipeworks_mud_mapper/commit/4e0d723e8528b382edfb811fd67cb672af969002))


### Fixes

* add workflow_dispatch trigger to CI for release-please ([f26ae5d](https://github.com/pipe-works/pipeworks_mud_mapper/commit/f26ae5dd032e08113fafbf13ea02128dff01327d))
* lower CI coverage threshold to 25% for skeleton phase ([5520f34](https://github.com/pipe-works/pipeworks_mud_mapper/commit/5520f346fb1df648b86d10279da5dde3bdbca34e))
* make version test check format not hardcoded value ([5009aee](https://github.com/pipe-works/pipeworks_mud_mapper/commit/5009aee8c1d037c8c702c415406d5033091d85e4))
* trigger CI on release-please branches ([fc50666](https://github.com/pipe-works/pipeworks_mud_mapper/commit/fc50666e428ff7a135fa3491c0a983355e12f786))
* update version test and add map_view tests ([fc85b6f](https://github.com/pipe-works/pipeworks_mud_mapper/commit/fc85b6fd09c86f31717ec9d7d3e40403c6268786))
