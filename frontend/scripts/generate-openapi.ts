import { execSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const currentFile = fileURLToPath(import.meta.url)
const scriptsDir = dirname(currentFile)
const frontendRoot = resolve(scriptsDir, '..')
const repoRoot = resolve(frontendRoot, '..')
const generatedDir = resolve(frontendRoot, 'src/api/generated')
const schemaPath = resolve(generatedDir, 'openapi.json')
const typesPath = resolve(generatedDir, 'openapi.d.ts')

mkdirSync(generatedDir, { recursive: true })

const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'

execSync(`${pythonCmd} "${resolve(repoRoot, 'scripts/export_openapi.py')}" "${schemaPath}"`, {
  cwd: repoRoot,
  stdio: 'inherit',
  shell: true,
})

execSync(`pnpm exec openapi-typescript "${schemaPath}" -o "${typesPath}"`, {
  cwd: frontendRoot,
  stdio: 'inherit',
  shell: true,
})
