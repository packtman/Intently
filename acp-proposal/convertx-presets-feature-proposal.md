# Feature Proposal: Conversion Presets

**Repository:** https://github.com/C4illin/ConvertX  
**Author:** [Your Name]  
**Date:** January 9, 2026

---

## Problem

Users frequently convert files with the same settings (e.g., "compress video to 720p H.264" or "convert images to WebP at 80% quality"). Currently, they must reconfigure options each time.

## Proposed Solution

Add a **Conversion Presets** feature allowing users to save, name, and reuse conversion configurations.

## Core Functionality

- **Save Preset**: After configuring a conversion, click "Save as Preset" to store the settings
- **Apply Preset**: Select a saved preset from a dropdown when starting a new conversion
- **Manage Presets**: Edit, rename, or delete saved presets from settings page

## Database Schema Addition

```sql
CREATE TABLE presets (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  input_format TEXT,
  output_format TEXT NOT NULL,
  options JSON NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## UI Changes

1. Add "Save as Preset" button on conversion success page
2. Add preset selector dropdown on main conversion page
3. Add "Presets" tab in user settings

## Scope

- User-scoped presets (each user manages their own)
- Optional: Admin can create "system presets" visible to all users

## Benefits

- Faster repeat workflows
- Consistent output quality across team members
- Reduces configuration errors

## Effort Estimate

Small - 2-3 days for a contributor familiar with the codebase

