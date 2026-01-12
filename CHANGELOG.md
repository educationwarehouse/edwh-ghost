# Changelog

<!--next-version-placeholder-->

## v0.1.0 (2026-01-12)

### Feature

* **resultset:** Allow chaining result sets with | to combine them ([`be9f2ab`](https://github.com/educationwarehouse/edwh-ghost/commit/be9f2abc9b69e11c30c6c6c6989054b4a779958c))
* **pytest:** Windows script to run pytest with coverage and verbose ([`a5de65b`](https://github.com/educationwarehouse/edwh-ghost/commit/a5de65b60cee1e7374ef154ff7939307395c27f5))
* **ghost:** Support v5 and test all supported api versions in pytest ([`e556c1c`](https://github.com/educationwarehouse/edwh-ghost/commit/e556c1c1a714ea00ba4982b32fb3139f8452e351))
* **pkg:** Specify py version required (3.7+) ([`7a1fe2c`](https://github.com/educationwarehouse/edwh-ghost/commit/7a1fe2ce3f0e7d922e090319a6e5a35c8efc55f8))
* **paginate:** Add .next() to resultset to get next page (if limited) ([`517fa1b`](https://github.com/educationwarehouse/edwh-ghost/commit/517fa1bae045685ba2c90b3e55a6d3fc6667e77a))
* **test:** Pytest github action ([`228d562`](https://github.com/educationwarehouse/edwh-ghost/commit/228d5626445152343ab97199595a65eb1da95bd5))
* **content:** Allow using only content api client (without admin key) for READs ([`334ffbe`](https://github.com/educationwarehouse/edwh-ghost/commit/334ffbe6afddb0508908d1462be0d57d39f5a2c2))
* **test:** Added pytest and pip-compile ([`c59bae6`](https://github.com/educationwarehouse/edwh-ghost/commit/c59bae6ed5ca9938551bfd0d0570577871348ac4))
* **authors:** .authors with same syntax as .posts etc ([`414c78b`](https://github.com/educationwarehouse/edwh-ghost/commit/414c78b2f513d65ef8f748f6f41f56373fa87b73))
* **api:** Easier methods (.posts, .tags and .pages) with filters etc in sane syntax ([`02398ce`](https://github.com/educationwarehouse/edwh-ghost/commit/02398ce04b761568fba8bbfb41ada2067d274da6))

### Fix

* Set version to 0.0.0 for python semantic release ([`4372b63`](https://github.com/educationwarehouse/edwh-ghost/commit/4372b634301d0ac718aa3c7027e4c0820c702b3b))
* Store version in python file instead of project definition ([`9003f80`](https://github.com/educationwarehouse/edwh-ghost/commit/9003f80009e1a8210dd59d16cf587e43e72df2b8))
* Improve ghost 5 and 6 support ([`5fb6acc`](https://github.com/educationwarehouse/edwh-ghost/commit/5fb6accb2e3788e7fe90bae818ac6c9587d3f3d1))
* **dependencies:** Removed pip-tools pins because that led to errors/dependency hell in some cases ([`2e76356`](https://github.com/educationwarehouse/edwh-ghost/commit/2e763564fcb14e9e33899373004dc4f85b0fffd4))
* ***:** Minor improvements that were missed previous version ([`bc295c9`](https://github.com/educationwarehouse/edwh-ghost/commit/bc295c94cf1e954a6fec8459d34e259ef0e534c1))
* **ghost:** Expose GhostContent as well as Ghost Admin ([`de35d14`](https://github.com/educationwarehouse/edwh-ghost/commit/de35d14b51228dc2d16972304c3d0e4e181eea65))
* **__all__:** Strings instead of types ([`145b82a`](https://github.com/educationwarehouse/edwh-ghost/commit/145b82a030a44706fd21bd88c6c168e3514c619e))
* **__all__:** More specific imports for * ([`d612084`](https://github.com/educationwarehouse/edwh-ghost/commit/d61208493e5a8bb258bfc32548e49c102cf494f0))
* **pip:** Pip-tools 6.6.2 works with the latest pip [ci skip] ([`13d4c58`](https://github.com/educationwarehouse/edwh-ghost/commit/13d4c58ffd8d14eb639426cc1b9b67291da57bfa))
* **syntax:** More 3.8 -> 3.7 syntax ([`c6bcee8`](https://github.com/educationwarehouse/edwh-ghost/commit/c6bcee88c5d156b288b1608071618840f13aea72))
* **test:** Tempfile as str ([`d741f05`](https://github.com/educationwarehouse/edwh-ghost/commit/d741f054846bb5f9ec7876a676e8e5d76d3527be))
* **ghost:** Replaced 3.8 syntax with 3.7 ([`f36d787`](https://github.com/educationwarehouse/edwh-ghost/commit/f36d787bfbf19b35e2fe5d2b6f54e9228913f905))
* **actions:** Don't run in parallel ([`91af311`](https://github.com/educationwarehouse/edwh-ghost/commit/91af3117b6fb0edfb317c8517c609427c2b532f4))
* **actions:** Secrets with env ([`2f77f60`](https://github.com/educationwarehouse/edwh-ghost/commit/2f77f60c075e5470d3882fc2182eff87c1017d8e))
* **action:** No fail fast (also run other versions on fail of one version) ([`0eaca28`](https://github.com/educationwarehouse/edwh-ghost/commit/0eaca28989520ffe6acffd181109ba9cdf5b2a15))
* **actions:** Py 3.6 is EOL ([`3907fdd`](https://github.com/educationwarehouse/edwh-ghost/commit/3907fdd50244480ad305952a0b198de96ef9afe5))
* **actions:** Use secrets/env ([`d9c263c`](https://github.com/educationwarehouse/edwh-ghost/commit/d9c263cbeaec86d76f2d731441116eb4585caea5))
* **test:** Fixed mistakes in tests and module ([`3784a13`](https://github.com/educationwarehouse/edwh-ghost/commit/3784a1393c0d48b5c2ebd6f8c2cdd5d16121a803))
* **action:** Wrong order ([`1045a00`](https://github.com/educationwarehouse/edwh-ghost/commit/1045a00218919c68aeee3a87dd7236508ef3968e))
* **action:** Install all required dependencies for testing ([`18565c4`](https://github.com/educationwarehouse/edwh-ghost/commit/18565c421981d6e57a881eed76500d133eefb6f8))
* **action:** 3.1 != 3.10 ([`94e1bdc`](https://github.com/educationwarehouse/edwh-ghost/commit/94e1bdc8966c332681f031f54311cd3f1a077fdf))
* **ghost:** Minor fixes ([`dc44bb3`](https://github.com/educationwarehouse/edwh-ghost/commit/dc44bb3aff30625164af7c3a583229d10c19b44b))
* **ghost:** Actually update headers on error/retry ([`6be83ee`](https://github.com/educationwarehouse/edwh-ghost/commit/6be83ee9f13197844000c9bceb49c9680070a128))

### Documentation

* **users:** User endpoint was already supported but tests and docs were missing ([`858867f`](https://github.com/educationwarehouse/edwh-ghost/commit/858867fe751781d222e191ef2389c01e1bef5aa8))
* **readme:** Added table with available and unsupported resources ([`340ea3d`](https://github.com/educationwarehouse/edwh-ghost/commit/340ea3d0d497b41a7f02484d8ea60a525ba98d83))
* **ghost:** Minor improvements [ci skip] ([`0044b5b`](https://github.com/educationwarehouse/edwh-ghost/commit/0044b5b5227f5e63f232768db8b97577417b23b2))
* Refactor and add return types in README example ([`4d7c113`](https://github.com/educationwarehouse/edwh-ghost/commit/4d7c11319fdf694cb5ea40e65f632e86fd324a46))
* Docstrings and readme ([`3de1c6a`](https://github.com/educationwarehouse/edwh-ghost/commit/3de1c6a79cd34c38f57090d4223fbe1008b10ae8))
* **ghost:** Improved docstrings ([`a754f0f`](https://github.com/educationwarehouse/edwh-ghost/commit/a754f0fda2a8f5868b077c9b6593f8294506222c))
