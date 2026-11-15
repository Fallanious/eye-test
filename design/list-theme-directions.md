# EYE TEST — minimal list themes

Design exploration only. The application is not changed. Block-letter wordmark; no player logo. Mockups use illustrative data and neutral video placeholders.

## Palettes

| Direction | Background | Surface | Text | Secondary | Accent |
| --- | --- | --- | --- | --- | --- |
| Film room | #151715 | #20231F | #F3F1E7 | #A6ACA3 | #E3AF56 |
| Courtside | #F5F3EC | #FFFFFF | #202B24 | #667168 | #286344 |
| Replay | #F3F6FA | #FFFFFF | #182433 | #647184 | #245BDB |

Film room emphasizes watching footage; Courtside emphasizes quiet browsing; Replay emphasizes a clear utility interface. Use accent sparingly for selected content, focus, and primary actions. Team codes stay neutral rather than introducing thirty team colors. Selection must also have a text/icon cue. Final implementation should verify contrast and keyboard focus states.

## Organization

- Desktop: searchable player list on the left, selected player and clip list on the right. Video sits above clips; keep the player summary compact. Selected player and playing clip remain clearly marked.
- Player rows: name first; team and position secondary; clip count at the right. Games belong in the selected-player summary, or an optional column in a full-width library. Default name sort; optional clip-count sort.
- Clip rows: play description first, game/opponent and quarter/clock secondary; duration aligned at the right. Filter by play role. In a larger archive, group by game with date and matchup in the group heading.
- Mobile: player library and player film are separate screens connected by a visible back action. Keep search and team filtering above the list. Stack row metadata below titles. Do not shrink desktop columns or require horizontal scrolling.
- Mobile video: inline above the clip list. Selecting a row updates that player; provide a visible route back to playback if the user is far down the list. Avoid a large sticky video that consumes the whole screen.
- Preserve the project's existing loading, empty, error, and load-more behavior. Show missing durations as a dash. Wrap long player names and descriptions rather than hiding essential meaning.

The proposed master-detail desktop layout is an exploration beyond the current grid-to-detail view. Existing fields already support the displayed metadata. Import is proposed user-facing shorthand for the current Upload/Download workflow.

## Generation

Concept boards generated with built-in imagegen. Exact prompts are saved separately alongside each board.
