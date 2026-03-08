import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { dirname, relative, resolve } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const currentFile = fileURLToPath(import.meta.url)
const scriptsDir = dirname(currentFile)
const frontendRoot = resolve(scriptsDir, '..')
const schemaPath = resolve(frontendRoot, 'src/api/generated/openapi.json')
const typesPath = resolve(frontendRoot, 'src/api/generated/openapi.d.ts')

const trackedFiles = [schemaPath, typesPath]

const criticalResponses = [
  { path: '/api/chat/send-stream', method: 'post', contentType: 'text/event-stream', expected: 'string' },
  { path: '/api/chat/review', method: 'post', contentType: 'application/json', expected: 'schema' },
  {
    path: '/api/documents/export',
    method: 'post',
    contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    expected: 'binary',
  },
  {
    path: '/api/documents/export-editor',
    method: 'post',
    contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    expected: 'binary',
  },
  {
    path: '/api/documents/history/{doc_id}/download',
    method: 'get',
    contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    expected: 'binary',
  },
] as const

interface OpenApiSchema {
  paths?: Record<string, Record<string, any>>
}

function run(command: string, cwd: string) {
  execSync(command, { cwd, stdio: 'inherit', shell: true })
}

function snapshot(path: string): string | null {
  try {
    return readFileSync(path, 'utf-8')
  }
  catch {
    return null
  }
}

function hasStructuredSchema(schema: any): boolean {
  if (!schema || typeof schema !== 'object') {
    return false
  }
  return Boolean(schema.$ref || schema.type || schema.oneOf || schema.anyOf || schema.allOf)
}

function assertCriticalResponses(schema: OpenApiSchema) {
  for (const item of criticalResponses) {
    const operation = schema.paths?.[item.path]?.[item.method]
    if (!operation) {
      throw new Error(`Missing OpenAPI operation: ${item.method.toUpperCase()} ${item.path}`)
    }
    const response = operation.responses?.['200']
    const media = response?.content?.[item.contentType]
    const responseSchema = media?.schema
    if (!responseSchema) {
      throw new Error(`Missing 200 schema for ${item.method.toUpperCase()} ${item.path} (${item.contentType})`)
    }
    if (item.expected === 'string' && responseSchema.type !== 'string') {
      throw new Error(`Expected string schema for ${item.method.toUpperCase()} ${item.path}`)
    }
    if (item.expected === 'binary' && !(responseSchema.type === 'string' && responseSchema.format === 'binary')) {
      throw new Error(`Expected binary schema for ${item.method.toUpperCase()} ${item.path}`)
    }
    if (item.expected === 'schema' && !hasStructuredSchema(responseSchema)) {
      throw new Error(`Expected structured JSON schema for ${item.method.toUpperCase()} ${item.path}`)
    }
  }
}

const before = new Map(trackedFiles.map(path => [path, snapshot(path)]))

run('pnpm run generate:openapi', frontendRoot)

const changedFiles = trackedFiles.filter(path => snapshot(path) !== before.get(path))
if (changedFiles.length) {
  console.error('OpenAPI generated artifacts are out of date. Regenerate and commit the updated files:')
  for (const path of changedFiles) {
    console.error(` - ${relative(frontendRoot, path)}`)
  }
  process.exit(1)
}

const schema = JSON.parse(readFileSync(schemaPath, 'utf-8')) as OpenApiSchema
assertCriticalResponses(schema)

console.log('OpenAPI generated artifacts are in sync.')
