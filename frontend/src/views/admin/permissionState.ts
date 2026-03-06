export interface AdminAccountsPermissionState {
  platformAdmin: boolean
  canWriteAccounts: boolean
  canCreateAccount: boolean
  canToggleAccountStatus: boolean
  canEditUserRoles: boolean
  canRebindUsers: boolean
  canCreateInvite: boolean
}

export interface AdminRolesPermissionState {
  canWriteRoles: boolean
}

export function getAdminAccountsPermissionState(permissionCodes: string[], accountId: number): AdminAccountsPermissionState {
  const platformAdmin = Number(accountId || 0) === 1
  const canWriteAccounts = permissionCodes.includes('accounts:write')
  return {
    platformAdmin,
    canWriteAccounts,
    canCreateAccount: platformAdmin && canWriteAccounts,
    canToggleAccountStatus: platformAdmin && canWriteAccounts,
    canEditUserRoles: canWriteAccounts,
    canRebindUsers: platformAdmin && canWriteAccounts,
    canCreateInvite: canWriteAccounts,
  }
}

export function getAdminRolesPermissionState(permissionCodes: string[]): AdminRolesPermissionState {
  return {
    canWriteRoles: permissionCodes.includes('accounts:write'),
  }
}
