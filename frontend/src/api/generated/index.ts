import type { components } from './openapi'

type Schema = components['schemas']

export type MessageResponse = Schema['MessageResponse']

export interface AuthUserResponse extends Omit<Schema['AuthUserResponse'], 'roles'> {
  roles: string[]
}

export interface AuthTokenResponse extends Omit<Schema['AuthTokenResponse'], 'user'> {
  user: AuthUserResponse
}

export interface PermissionCodesResponse extends Omit<Schema['PermissionCodesResponse'], 'permissions'> {
  permissions: string[]
}

export interface ProfileUpdateResponse extends Omit<Schema['ProfileUpdateResponse'], 'user'> {
  user: AuthUserResponse
}

export type AccountResponse = Schema['AccountResponse']

export interface AccountListResponse extends Omit<Schema['AccountListResponse'], 'items'> {
  items: AccountResponse[]
}

export type PermissionInfoResponse = Schema['PermissionInfoResponse']

export interface PermissionListResponse extends Omit<Schema['PermissionListResponse'], 'items'> {
  items: PermissionInfoResponse[]
}

export interface RoleInfoResponse extends Omit<Schema['RoleInfoResponse'], 'permissions'> {
  permissions: string[]
}

export interface RoleListResponse extends Omit<Schema['RoleListResponse'], 'items'> {
  items: RoleInfoResponse[]
}

export type UserRoleSummaryResponse = Schema['UserRoleSummaryResponse']

export interface AccountUserResponse extends Omit<Schema['AccountUserResponse'], 'role_codes' | 'roles'> {
  role_codes: string[]
  roles: UserRoleSummaryResponse[]
}

export interface AccountUsersResponse extends Omit<Schema['AccountUsersResponse'], 'items'> {
  items: AccountUserResponse[]
}

export type AccountInviteResponse = Schema['AccountInviteResponse']

export interface AccountInviteListResponse extends Omit<Schema['AccountInviteListResponse'], 'items'> {
  items: AccountInviteResponse[]
}

export type InviteStatusResponse = Schema['InviteStatusResponse']
export type RoleDeleteResponse = Schema['RoleDeleteResponse']
export type RebindUserResponse = Schema['RebindUserResponse']

export interface UserRoleUpdateResponse extends Omit<Schema['UserRoleUpdateResponse'], 'role_codes'> {
  role_codes: string[]
}

export type ChatSessionResponse = Schema['ChatSessionResponse']

export interface ChatSessionListResponse extends Omit<Schema['ChatSessionListResponse'], 'items'> {
  items: ChatSessionResponse[]
}

export type ChatMessageResponse = Schema['ChatMessageResponse']

export interface ChatMessageListResponse extends Omit<Schema['ChatMessageListResponse'], 'items'> {
  items: ChatMessageResponse[]
}

export type ChatReplyResponse = Schema['ChatReplyResponse']

export interface ChatWorkflowSseEventResponse extends Omit<Schema['ChatWorkflowSseEventResponse'], 'detail'> {
  detail?: string
}

export type ChatChunkSseEventResponse = Schema['ChatChunkSseEventResponse']
export type ChatErrorSseEventResponse = Schema['ChatErrorSseEventResponse']

export interface ChatFinalSseEventResponse extends Omit<Schema['ChatFinalSseEventResponse'], 'message' | 'warnings'> {
  message: ChatMessageResponse
  warnings?: string[]
}

export type ChatStreamEventResponse
  = | ChatWorkflowSseEventResponse
    | ChatChunkSseEventResponse
    | ChatErrorSseEventResponse
    | ChatFinalSseEventResponse

export interface SessionDraftResponse extends Omit<Schema['SessionDraftResponse'], 'draft'> {
  draft: Record<string, unknown>
}

export interface MaterialResponse extends Omit<Schema['MaterialResponse'], 'keywords'> {
  keywords: string[]
}

export interface MaterialUploadResponse extends Omit<Schema['MaterialUploadResponse'], 'keywords'> {
  keywords: string[]
}

export interface MaterialListResponse extends Omit<Schema['MaterialListResponse'], 'items'> {
  items: MaterialResponse[]
}

export type UploadTaskResponse = Schema['UploadTaskResponse']

export type BookImportStartResponse = Schema['BookImportStartResponse']
export type BookImportFileResultResponse = Schema['BookImportFileResultResponse']

export interface BookImportTaskResponse extends Omit<Schema['BookImportTaskResponse'], 'file_results' | 'selected_files'> {
  file_results: BookImportFileResultResponse[]
  selected_files: string[]
}

export type BookScanItemResponse = Schema['BookScanItemResponse']

export interface BookScanResponse extends Omit<Schema['BookScanResponse'], 'items'> {
  items: BookScanItemResponse[]
}

export interface BookSourceResponse extends Omit<Schema['BookSourceResponse'], 'keywords' | 'metadata'> {
  keywords: string[]
  metadata: Record<string, unknown>
}

export interface BookSourceListResponse extends Omit<Schema['BookSourceListResponse'], 'items'> {
  items: BookSourceResponse[]
}

export type BookUploadErrorResponse = Schema['BookUploadErrorResponse']

export interface BookUploadResponse extends Omit<Schema['BookUploadResponse'], 'items' | 'errors'> {
  items: BookScanItemResponse[]
  errors: BookUploadErrorResponse[]
}

export type GeneratedDocumentHistoryItemResponse = Schema['GeneratedDocumentHistoryItemResponse']

export interface GeneratedDocumentHistoryListResponse extends Omit<Schema['GeneratedDocumentHistoryListResponse'], 'items'> {
  items: GeneratedDocumentHistoryItemResponse[]
}

export type PreferencesResponse = Schema['PreferencesResponse']
