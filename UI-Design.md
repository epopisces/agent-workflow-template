# User Interface Design Document: Multi-Agent Workflow Assistant

**Design Direction**: Focus Stream  
**Platform**: Streamlit Web App (Desktop-optimized)  
**Theme Default**: Dark Mode

---

## Layout Structure

### Primary Layout
Single-column centered layout with collapsible sidebar. Optimized for secondary monitor placement.

```
+------------------------------------------------------------------+
|  [≡]                      App Title                    [⚙]  [?]  |
+------+-----------------------------------------------------------+
|      |                                                           |
| T    |                                                           |
| H    |              Chat Message Area                            |
| R    |              (vertically scrolling)                       |
| E    |                                                           |
| A    |              Max-width: 720px                             |
| D    |              Centered horizontally                        |
| S    |                                                           |
|      |                                                           |
+------+-----------------------------------------------------------+
|      |   [ Drop files here or type message...      ] [Send ➤]   |
+------+-----------------------------------------------------------+
```

### Sidebar Behavior
- **Collapsed State**: 48px rail showing thread icons only
- **Expanded State**: 280px panel with thread previews and timestamps
- **Trigger**: Hover (300ms delay) or click hamburger icon
- **Auto-collapse**: When mouse leaves sidebar area

### Inspector Drawer (Power User)
- **Trigger**: Ctrl+I keyboard shortcut or click status indicator
- **Position**: Slides in from right edge, 360px width
- **Content**: Agent activity log, reasoning chain, debug output
- **Dismiss**: Same shortcut, click outside, or Escape key

---

## Core Components

### Header Bar
- Hamburger menu icon (left) - toggles sidebar
- App title centered
- Settings gear icon (right)
- Help icon (right)
- Height: 48px

### Thread List (Sidebar)
- New Chat button at top (primary action)
- Scrollable thread list below
- Each thread shows: Title (auto-generated or user-set), timestamp, 1-line preview
- Active thread highlighted
- Hover reveals delete/rename icons

### Chat Message Area
- Max-width container (720px) centered in available space
- Generous vertical padding between messages (24px)
- Clear visual separation between user and assistant messages
- Timestamps shown on hover
- Code blocks with syntax highlighting and copy button

### Message Bubbles
- **User Messages**: Right-aligned, accent background, rounded corners
- **Assistant Messages**: Left-aligned, subtle background, rounded corners
- **System Messages**: Centered, muted text, no background

### Input Area
- Multi-line text input (auto-expands to 4 lines max)
- Placeholder text: "Ask a question or drop files here..."
- Send button (right side)
- File attachment indicator (shows queued files as dismissible chips)
- Character/token count (subtle, bottom-right)

### Drop Zone
- **Inactive**: Invisible
- **Active (drag detected)**: Entire chat area shows subtle border glow and "Drop files here" overlay
- **Supported indicators**: Show accepted file type icons during drag

### Status Indicator
- Small pill in header showing agent status
- States: Idle (hidden), Thinking (pulsing dot), Processing (agent name)
- Clickable to open Inspector Drawer

---

## Interaction Patterns

### Message Submission
- Enter key sends message (Shift+Enter for newline)
- Send button click sends message
- Input clears after send
- Scroll to bottom on new message

### File Handling
- Drag files anywhere in chat area
- Click input area to open file picker (future)
- Queued files appear as chips above input
- Click X on chip to remove before sending
- Supported: .txt, .md (future: .pdf, images)

### Thread Management
- Click thread to switch (auto-saves current)
- New Chat clears input and messages, creates new thread
- Thread auto-titles from first message
- Right-click thread for rename/delete menu

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| Ctrl+I | Toggle Inspector Drawer |
| Ctrl+N | New Chat |
| Ctrl+K | Focus search/command (future) |
| Escape | Close drawers/modals |
| Up Arrow (in empty input) | Edit last message |

### Loading States
- Typing indicator (three animated dots) for assistant responses
- Skeleton loaders for thread list on initial load
- Subtle progress animation in status pill during processing

### Error Handling
- Inline error messages below failed operations
- Retry button for failed message sends
- Toast notifications for background errors (auto-dismiss 5s)

---

## Visual Design Elements & Color Scheme

### Dark Theme (Default)

| Element | Color | Hex |
|---------|-------|-----|
| Background (primary) | Near-black | #0D0D0F |
| Background (secondary) | Dark gray | #18181B |
| Background (elevated) | Medium gray | #27272A |
| Text (primary) | Off-white | #FAFAFA |
| Text (secondary) | Gray | #A1A1AA |
| Text (muted) | Dark gray | #52525B |
| Accent (primary) | Soft blue | #60A5FA |
| Accent (hover) | Lighter blue | #93C5FD |
| User message bg | Accent dimmed | #1E3A5F |
| Assistant message bg | Elevated | #27272A |
| Border | Subtle | #3F3F46 |
| Success | Green | #4ADE80 |
| Warning | Amber | #FBBF24 |
| Error | Red | #F87171 |

### Light Theme (Configurable)

| Element | Color | Hex |
|---------|-------|-----|
| Background (primary) | White | #FFFFFF |
| Background (secondary) | Light gray | #F4F4F5 |
| Background (elevated) | White | #FFFFFF |
| Text (primary) | Near-black | #18181B |
| Text (secondary) | Gray | #71717A |
| Accent (primary) | Blue | #3B82F6 |
| User message bg | Accent light | #DBEAFE |
| Assistant message bg | Light gray | #F4F4F5 |
| Border | Light gray | #E4E4E7 |

### Visual Effects
- Subtle shadows on elevated elements (cards, drawers)
- Smooth transitions (150ms ease) on hovers and state changes
- Gentle glow on drop zone activation
- No harsh borders—use subtle color differentiation

### Iconography
- Outline style icons (consistent stroke weight)
- 20px default size, 16px for inline
- Muted color by default, accent on hover/active

---

## Mobile, Web App, Desktop Considerations

### Desktop (Primary Target)
- Optimized for 1920x1080 and above
- Works well at narrower widths (min-width: 600px)
- Secondary monitor friendly (not dependent on full attention)
- Sidebar hover behavior for quick thread access

### Web App (Streamlit)
- Single-page application
- No native browser back/forward (handle in-app)
- Local storage for preferences (theme, sidebar state)
- Responsive but not mobile-optimized

### Tablet/Mobile (Future Consideration)
- Below 768px: Sidebar becomes full-screen overlay
- Below 480px: Simplified layout (not priority)
- Touch targets minimum 44px
- Swipe gestures for drawer navigation

### Window Sizing
- Graceful degradation at smaller sizes
- Chat column maintains max-width regardless of window size
- Sidebar collapses automatically below 900px width

---

## Typography

### Font Stack
- **Primary**: Inter (system-ui fallback)
- **Monospace**: JetBrains Mono, Fira Code, monospace

### Scale

| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| App Title | 18px | 600 | 1.2 |
| Message Text | 15px | 400 | 1.6 |
| Message Bold | 15px | 600 | 1.6 |
| Code Inline | 14px | 400 | 1.4 |
| Code Block | 13px | 400 | 1.5 |
| Timestamp | 12px | 400 | 1.2 |
| Label/Caption | 12px | 500 | 1.2 |
| Thread Title | 14px | 500 | 1.3 |
| Thread Preview | 13px | 400 | 1.4 |
| Button | 14px | 500 | 1.0 |

### Text Rendering
- Antialiased rendering
- Proper letter-spacing for all-caps labels (+0.5px)
- Hyphenation disabled in chat messages
- Word-break on long URLs/code

---

## Accessibility

### Color & Contrast
- Minimum 4.5:1 contrast ratio for body text
- Minimum 3:1 for large text and UI components
- Color not sole indicator of state (icons + color)
- Tested with color blindness simulators

### Keyboard Navigation
- Full keyboard accessibility (Tab, Shift+Tab, Enter, Escape)
- Visible focus indicators (2px accent outline)
- Skip-to-content link (hidden until focused)
- Logical tab order (sidebar → chat → input)

### Screen Readers
- Semantic HTML structure (headings, landmarks, lists)
- ARIA labels on icon-only buttons
- Live regions for new messages and status updates
- Alt text for any images/icons with meaning

### Motion & Animation
- Respects prefers-reduced-motion
- All animations under 200ms
- No auto-playing animations that can't be stopped
- Status indicators use shape/text in addition to animation

### Text & Readability
- Resizable text (rem-based sizing)
- Sufficient line-height (1.5+ for body)
- Maximum line length ~75 characters
- No justified text

### Configuration Options
- Theme toggle (dark/light/system)
- Font size adjustment (future)
- Reduced motion toggle in settings
- High contrast mode (future)

---

## Configuration (Theme Customization)

Themes configurable via `config.yaml`:

```yaml
ui:
  theme: dark  # dark | light | system
  accent_color: "#60A5FA"
  font_family: "Inter"
  font_size_base: 15
  sidebar_default: collapsed  # collapsed | expanded
  inspector_shortcut: "ctrl+i"
  animations: true  # respects prefers-reduced-motion regardless
```

---

*Document Version: 1.0*  
*Last Updated: December 2024*
