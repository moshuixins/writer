import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import adminRoutes from '../src/router/modules/admin'
import { filterMenusByAuth, findFirstAccessibleChildRoute, hasAllPermissions, hasAnyPermission } from '../src/utils/permission'
import { getAdminAccountsPermissionState, getAdminRolesPermissionState } from '../src/views/admin/permissionState'

function createAuth(permissionCodes: string[]) {
  return (value: string | string[]) => hasAnyPermission(permissionCodes, value)
}

function testPermissionHelpers() {
  assert.equal(hasAnyPermission(['accounts:read'], 'accounts:read'), true)
  assert.equal(hasAnyPermission(['accounts:read'], 'accounts:write'), false)
  assert.equal(hasAnyPermission(['accounts:read'], ['accounts:write', 'accounts:read']), true)
  assert.equal(hasAllPermissions(['accounts:read', 'accounts:write'], ['accounts:read', 'accounts:write']), true)
  assert.equal(hasAllPermissions(['accounts:read'], ['accounts:read', 'accounts:write']), false)
}

function testAdminRoutePermissions() {
  assert.ok(Array.isArray(adminRoutes.children) && adminRoutes.children.length > 0, 'admin route children missing')
  adminRoutes.children?.forEach((child) => {
    assert.equal(child.meta?.auth, 'accounts:read', `admin child route ${String(child.name)} missing accounts:read auth`)
  })
}

function testMenuFiltering() {
  const menus = [
    {
      meta: { title: '管理后台' as const },
      children: [
        {
          path: '/admin/accounts',
          meta: { title: '账户管理' as const, auth: 'accounts:read' },
        },
      ],
    },
    {
      meta: { title: '素材' as const },
      children: [
        {
          path: '/writer/materials',
          meta: { title: '素材管理' as const, auth: 'materials:read' },
        },
      ],
    },
  ]

  const noAdminMenus = filterMenusByAuth(menus, createAuth(['materials:read']))
  assert.equal(noAdminMenus.length, 1)
  assert.equal(noAdminMenus[0].meta?.title, '素材')

  const withAdminMenus = filterMenusByAuth(menus, createAuth(['materials:read', 'accounts:read']))
  assert.equal(withAdminMenus.length, 2)
  assert.equal(withAdminMenus[0].children?.[0].path, '/admin/accounts')
}

function testRedirectGuardSelection() {
  const children = [
    {
      path: '/admin/hidden',
      meta: { menu: false, auth: 'accounts:read' },
    },
    {
      path: '/admin/accounts',
      meta: { auth: 'accounts:read' },
    },
    {
      path: '/admin/roles',
      meta: { auth: 'accounts:write' },
    },
  ]

  const readRoute = findFirstAccessibleChildRoute(children, createAuth(['accounts:read']))
  assert.equal(readRoute?.path, '/admin/accounts')

  const writeRoute = findFirstAccessibleChildRoute(children, createAuth(['accounts:write']))
  assert.equal(writeRoute?.path, '/admin/roles')

  const noneRoute = findFirstAccessibleChildRoute(children, createAuth(['materials:read']))
  assert.equal(noneRoute, undefined)
}

function testAdminPermissionState() {
  const readOnlyAccounts = getAdminAccountsPermissionState(['accounts:read'], 1)
  assert.equal(readOnlyAccounts.platformAdmin, true)
  assert.equal(readOnlyAccounts.canWriteAccounts, false)
  assert.equal(readOnlyAccounts.canCreateAccount, false)
  assert.equal(readOnlyAccounts.canToggleAccountStatus, false)
  assert.equal(readOnlyAccounts.canEditUserRoles, false)
  assert.equal(readOnlyAccounts.canRebindUsers, false)
  assert.equal(readOnlyAccounts.canCreateInvite, false)

  const platformWriter = getAdminAccountsPermissionState(['accounts:read', 'accounts:write'], 1)
  assert.equal(platformWriter.canCreateAccount, true)
  assert.equal(platformWriter.canToggleAccountStatus, true)
  assert.equal(platformWriter.canEditUserRoles, true)
  assert.equal(platformWriter.canRebindUsers, true)
  assert.equal(platformWriter.canCreateInvite, true)

  const scopedWriter = getAdminAccountsPermissionState(['accounts:read', 'accounts:write'], 2)
  assert.equal(scopedWriter.platformAdmin, false)
  assert.equal(scopedWriter.canCreateAccount, false)
  assert.equal(scopedWriter.canToggleAccountStatus, false)
  assert.equal(scopedWriter.canEditUserRoles, true)
  assert.equal(scopedWriter.canRebindUsers, false)
  assert.equal(scopedWriter.canCreateInvite, true)

  const roleReadOnly = getAdminRolesPermissionState(['accounts:read'])
  assert.equal(roleReadOnly.canWriteRoles, false)

  const roleWriter = getAdminRolesPermissionState(['accounts:read', 'accounts:write'])
  assert.equal(roleWriter.canWriteRoles, true)
}

function testAdminTemplateBindings() {
  const adminAccountsPath = fileURLToPath(new URL('../src/views/admin/AdminAccounts.vue', import.meta.url))
  const adminAccountsListPath = fileURLToPath(new URL('../src/views/admin/components/AdminAccountsList.vue', import.meta.url))
  const adminAccountUsersPath = fileURLToPath(new URL('../src/views/admin/components/AdminAccountUsersTab.vue', import.meta.url))
  const adminAccountInvitesPath = fileURLToPath(new URL('../src/views/admin/components/AdminAccountInvitesTab.vue', import.meta.url))
  const adminRolesPath = fileURLToPath(new URL('../src/views/admin/AdminRoles.vue', import.meta.url))
  const adminAccountsSource = readFileSync(adminAccountsPath, 'utf8')
  const adminAccountsListSource = readFileSync(adminAccountsListPath, 'utf8')
  const adminAccountUsersSource = readFileSync(adminAccountUsersPath, 'utf8')
  const adminAccountInvitesSource = readFileSync(adminAccountInvitesPath, 'utf8')
  const adminRolesSource = readFileSync(adminRolesPath, 'utf8')

  assert.match(adminAccountsSource, /v-if="canCreateAccount" type="primary" @click="createDialogVisible = true"/)
  assert.match(adminAccountsSource, /:can-toggle-account-status="canToggleAccountStatus"/)
  assert.match(adminAccountsSource, /:can-edit-user-roles="canEditUserRoles"/)
  assert.match(adminAccountsSource, /:can-rebind-users="canRebindUsers"/)
  assert.match(adminAccountsSource, /:can-create-invite="canCreateInvite"/)

  assert.match(adminAccountsListSource, /v-if="canToggleAccountStatus" label="[^"]+" width="116"/)
  assert.match(adminAccountUsersSource, /:disabled="!canEditUserRoles \|\| !roleOptions\.length \|\| savingUserId === row\.id"/)
  assert.match(adminAccountUsersSource, /v-if="canRebindUsers" label="[^"]+" width="120"/)
  assert.match(adminAccountInvitesSource, /v-if="canCreateInvite" type="primary" :disabled="!currentAccount" @click="emit\('open-invite'\)"/)

  assert.match(adminRolesSource, /v-if="canWriteRoles" type="primary" :disabled="!selectedAccountId" @click="openCreateDialog"/)
  assert.match(adminRolesSource, /v-if="canWriteRoles" size="small" :disabled="row\.is_system" @click="openEditDialog\(row\)"/)
  assert.match(adminRolesSource, /v-if="canWriteRoles" size="small" type="danger" :disabled="row\.is_system" @click="removeRole\(row\)"/)
  assert.match(adminRolesSource, /v-if="canWriteRoles" type="primary" :loading="submitting" @click="submitRole"/)
}


const tests = [
  ['permission helpers', testPermissionHelpers],
  ['admin route permissions', testAdminRoutePermissions],
  ['menu filtering', testMenuFiltering],
  ['redirect guard selection', testRedirectGuardSelection],
  ['admin permission state', testAdminPermissionState],
  ['admin template bindings', testAdminTemplateBindings],
] as const

for (const [name, test] of tests) {
  test()
  console.log(`ok - ${name}`)
}

console.log(`permission regression passed: ${tests.length} checks`)

