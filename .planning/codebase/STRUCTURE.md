# STRUCTURE.md — File & Directory Layout

> Generated: 2026-03-18

```
ARIES-LITE/
├── main.py                          # Entry point — calls start_server_and_logic()
├── requirements.txt                 # 11 pinned dependencies
├── README.md                        # Project documentation
├── CHANGELOG.md                     # Version history
├── LICENSE                          # Project license
├── VERSION                          # Version string file
├── PROJECT_RULES.md                 # GSD methodology rules
├── GSD-STYLE.md                     # GSD style guide
├── CLAUDE.md                        # Claude Code instructions
├── model_capabilities.yaml          # Model capability definitions
│
├── src/                             # Core Python modules
│   ├── __init__.py                  # Package init (empty)
│   ├── config.py                    # All tuning constants (PID, servo, camera)
│   ├── camera.py                    # VideoStream — async frame capture
│   ├── vision.py                    # HybridVision — HAAR + CSRT + async dlib
│   ├── tracker.py                   # TrackerMachine — state machine + PID
│   └── hardware.py                  # PanTiltSystem — servo abstraction + mock
│
├── web/                             # Flask web application
│   ├── server.py                    # Routes, MJPEG stream, main_loop(), init
│   └── templates/
│       └── index.html               # Mobile-first Polish UI (single page)
│
├── adapters/                        # (Unused/empty — future adapter pattern?)
├── docs/                            # Documentation files
├── scripts/                         # Validation scripts
│   ├── validate-all.sh
│   └── validate-workflows.sh
│
├── .gsd/                            # OLD GSD artifacts (pre-.planning era)
│   ├── STATE.md
│   ├── SPEC.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md
│   ├── phases/1/1-PLAN.md
│   ├── templates/                   # GSD templates
│   └── examples/                    # GSD examples
│
├── .claude/                         # Claude Code config
├── .agent/                          # Agent config
├── .gemini/                         # Gemini config
└── .gitignore
```

## Key Observations
- **Flat src/**: 5 modules + __init__.py, no sub-packages
- **Single HTML template**: No static assets directory, CSS/JS inline
- **No tests directory**: No unit/integration tests exist
- **tmp_faces/**: Created at runtime for uploaded target images (in .gitignore)
- **adapters/**: Empty directory, potentially for future hardware abstraction
- **Total Python LOC**: ~400 lines across 6 files
