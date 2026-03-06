export type PermissionValue = string | string[]

export interface PermissionRouteLike {
  meta?: {
    auth?: PermissionValue
    menu?: boolean
  }
}

export interface PermissionMenuLike {
  meta?: {
    auth?: PermissionValue
    menu?: boolean
  }
  children?: PermissionMenuLike[]
}

export function hasPermission(permissionCodes: string[], permission: string) {
  if (!permission) {
    return true
  }
  return permissionCodes.includes(permission)
}

export function hasAnyPermission(permissionCodes: string[], value: PermissionValue) {
  if (typeof value === 'string') {
    return value !== '' ? hasPermission(permissionCodes, value) : true
  }
  return value.length > 0 ? value.some(item => hasPermission(permissionCodes, item)) : true
}

export function hasAllPermissions(permissionCodes: string[], value: string[]) {
  return value.length > 0 ? value.every(item => hasPermission(permissionCodes, item)) : true
}

export function findFirstAccessibleChildRoute<T extends PermissionRouteLike>(
  children: T[] | undefined,
  authCheck: (value: PermissionValue) => boolean,
) {
  return children?.find(route => route.meta?.menu !== false && authCheck(route.meta?.auth ?? ''))
}

export function filterMenusByAuth<T extends PermissionMenuLike>(
  menus: T[],
  authCheck: (value: PermissionValue) => boolean,
): T[] {
  const result: T[] = []
  menus.forEach((menu) => {
    if (!authCheck(menu.meta?.auth ?? '')) {
      return
    }

    const nextMenu = {
      ...menu,
    }

    if (menu.children && menu.children.length > 0) {
      const nextChildren = filterMenusByAuth(menu.children as T[], authCheck)
      if (nextChildren.length === 0) {
        return
      }
      nextMenu.children = nextChildren as T['children']
    }
    else {
      delete nextMenu.children
    }

    result.push(nextMenu as T)
  })
  return result
}
