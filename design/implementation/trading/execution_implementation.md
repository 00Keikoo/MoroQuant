# Execution Implementation Guide

## Design Source
- **Stitch Folder**: `design/stitch/current/execution_monitor`
- **Source Files**: `code.html`, `screen.png`

## Purpose
Guide the frontend implementation of the Execution workspace using existing styles and assets.

## Files to Modify
- `app/layout.tsx` (Update routing navigation lists if needed)
- `components/layout/sidebar.tsx` (Ensure link is active in sidebar)

## Files to Create
- `app/trading/execution/page.tsx` (Main workspace view)
- `components/execution/` (Domain-specific layout items if not present in MQDS)

## MQDS Components
- Buttons, Sidebar, Page Headers, Status Pills, Tables, Input Fields.

## Routing
- **Route**: `/trading/execution`

## Required APIs
- `GET `/api/execution/latency` (Returns system latency and order flow telemetry)`

## Temporary Mock Data
- Shape should mirror output of API schema. Keep initial mock in `lib/mock-data/execution-mock.json`.

## Future Production APIs
- FastAPI routes in `ml_service/api/` matching request/responses.

## Implementation Rules
1. **Pixel Perfect**: Reference `design/stitch/current/execution_monitor/code.html` and `design/stitch/current/execution_monitor/screen.png`.
2. **Reuse MQDS**: Do not create custom styling variables. Use existing token scales.
3. **No Redesign**: Implement layout as shown in the Stitch design folder.
4. **Responsive**: Ensure columns stack appropriately on mobile/smaller viewports.
5. **Accessibility**: All interactive elements must have unique, descriptive IDs and aria labels.
6. **Build Verification**: Run `npm run build` and ensure zero errors or warnings before committing.
7. **Commit**: Save changes under a dedicated workspace Git checkpoint.
8. **Stop**: Once build passes and code is committed, halt tasks.
