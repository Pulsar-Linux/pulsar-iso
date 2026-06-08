# Agent Instructions

## Git Configuration
Before making any commits, always run:

```bash
git config user.name "Celestia Ludenberg"
git config user.email "ash8820@proton.me"
```

This must be done in **every session** before committing or pushing. Do not use any default git identity.

## Repository
- Arch Linux live ISO based on EndeavourOS-ISO
- Provides KDE Plasma live environment with Cnchi installer
- Build with: `./prepare.sh && sudo ./mkarchiso -v "."`
