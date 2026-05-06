# MakeYourBrick Web Shell

This is Milestone UI-1: a local, static image upload and object selection shell.

## Run

Open `apps/web/index.html` in a browser.

No package installation or dev server is required for this milestone.

## Features

- image upload by file picker or drag and drop
- point selection
- box selection
- positive and negative point labels
- translucent mock mask overlay
- selection payload preview in image coordinates
- LEGO conversion settings preview
- JSON export for the selection/config payload

## Scope

This milestone does not call the Python backend, SAM segmentation, or SAM 3D Objects. It defines the browser-side interaction and payload shape that later backend milestones can consume.

