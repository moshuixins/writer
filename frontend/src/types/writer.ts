import type {
  AccountInviteResponse as ApiAccountInviteResponse,
  AccountResponse as ApiAccountResponse,
  AccountUserResponse as ApiAccountUserResponse,
  AuthUserResponse as ApiAuthUserResponse,
  BookImportFileResultResponse as ApiBookImportFileResultResponse,
  BookImportTaskResponse as ApiBookImportTaskResponse,
  BookScanItemResponse as ApiBookScanItemResponse,
  BookSourceResponse as ApiBookSourceResponse,
  BookUploadResponse as ApiBookUploadResponse,
  ChatMessageResponse as ApiChatMessageResponse,
  ChatSessionResponse as ApiChatSessionResponse,
  ChatWorkflowSseEventResponse as ApiChatWorkflowSseEventResponse,
  GeneratedDocumentHistoryItemResponse as ApiGeneratedDocumentHistoryItemResponse,
  MaterialResponse as ApiMaterialResponse,
  PermissionInfoResponse as ApiPermissionInfoResponse,
  PreferencesResponse as ApiPreferencesResponse,
  RoleInfoResponse as ApiRoleInfoResponse,
  SessionDraftResponse as ApiSessionDraftResponse,
  UserRoleSummaryResponse as ApiUserRoleSummaryResponse,
} from '@/api/generated'

// Canonical doc_type follows the 79 subtype catalog + "其他" fallback.
export type DocType = string

export interface ChatSession extends ApiChatSessionResponse {}

export interface PagedResult<T> {
  items: T[]
  total: number
}

export interface MaterialListParams {
  skip?: number
  limit?: number
  doc_type?: DocType
  keyword?: string
}

export interface ChatMessage extends ApiChatMessageResponse {
  warnings?: string[]
  workflow_steps?: ChatWorkflowStep[]
}

export interface ChatWorkflowStep {
  id: string
  step: string
  status: ApiChatWorkflowSseEventResponse['status']
  detail?: string
}

export interface Material extends ApiMaterialResponse {}

export interface BookScanItem extends ApiBookScanItemResponse {}

export interface BookImportFileResult extends ApiBookImportFileResultResponse {}

export type BookUploadError = ApiBookUploadResponse['errors'][number]

export interface BookUploadResult extends ApiBookUploadResponse {}

export interface BookImportTask extends ApiBookImportTaskResponse {}

export interface BookSourceRecord extends ApiBookSourceResponse {}

export interface ExportDoc extends ApiGeneratedDocumentHistoryItemResponse {}

export interface UserInfo extends ApiAuthUserResponse {}

export interface Account extends ApiAccountResponse {}

export interface UserRoleSummary extends ApiUserRoleSummaryResponse {}

export interface AccountUser extends ApiAccountUserResponse {}

export interface AccountInvite extends ApiAccountInviteResponse {}

export interface PermissionInfo extends ApiPermissionInfoResponse {}

export interface RoleInfo extends ApiRoleInfoResponse {}

export interface Preferences extends ApiPreferencesResponse {
  default_tone: 'formal' | 'semi-formal'
}

export interface ExportDocPayload {
  content_json: Record<string, unknown>
  title: string
  doc_type: DocType
  session_id?: number
}

export interface WriterDraft {
  title: string
  recipients: string
  body_json: Record<string, unknown>
  signing_org: string
  date: string
}

export interface SessionDraftResponse extends Omit<ApiSessionDraftResponse, 'draft'> {
  draft: WriterDraft
}

export interface SaveDraftPayload {
  save_mode: 'auto' | 'manual'
  draft: WriterDraft
}

export interface ExportEditorPayload {
  session_id: number
  doc_type: DocType
  draft: WriterDraft
}
