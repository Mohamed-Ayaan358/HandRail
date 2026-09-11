# HandRail

A local-first browser extension that gives unlabeled buttons, links, and images meaningful names for screen readers.

HandRail combines simple rules, cached labels, and optional AI models running on your own machine. The goal is to make browsing more accessible without sending page content to a cloud service.

## Planned features

- Generate missing accessible names while preserving existing labels.
- Work in rules-only mode without downloading a model.
- Use optional local text and vision models for harder cases.
- Let users review, edit, and undo generated labels.

## Status

In the design stage. No installable build is available yet.

See the [design document](DESIGN.md) for the architecture, implementation roadmap, and evaluation plan.

## Roadmap

The design proposes these phases, with roughly 12 weeks of estimated work:

- [ ] **0. Quality pilot (1 week):** test label quality before building the full system.
- [ ] **1. Rules-only extension (2 weeks):** detect missing names, apply rules, and export findings.
- [ ] **2. Local text inference (2 weeks):** add the Rust daemon, local model, and cache.
- [ ] **3. Scheduling (1 week):** prioritize upcoming controls, stream labels, and announce late results.
- [ ] **4. Desktop app (2 weeks):** add the tray UI, model downloads, and per-site settings.
- [ ] **5. Vision and developer tools (2 weeks):** support image descriptions and a DevTools panel.
- [ ] **6. Evaluation and release (2 weeks):** test with screen reader users and prepare distribution.

## License

[MIT](LICENSE). Model weights are subject to their own licenses.
