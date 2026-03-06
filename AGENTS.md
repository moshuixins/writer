# AGENTS.md

## PowerShell Encoding Guard

1. In this repo, dot-source `scripts/powershell_utf8.ps1` before any PowerShell command that prints or writes Chinese text.
2. Never write repository text files with `Set-Content`, `Add-Content`, `Out-File`, `>` or `>>`.
3. Prefer `apply_patch` for edits. If PowerShell must write a file, use `Write-Utf8NoBomFile` or `Append-Utf8NoBomFile` from `scripts/powershell_utf8.ps1`.
4. Do not use large PowerShell here-strings to generate Chinese-heavy files. They are easy to corrupt in tool transport.
5. If you need to normalize an existing file, use `Convert-FileToUtf8NoBom` or `python scripts/check_text_encoding.py --all --fix-bom`.
