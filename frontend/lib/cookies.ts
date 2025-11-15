// lib/cookies.ts

/**
 * Get a cookie value by name
 */
export function getCookie(name: string): string | null {
    if (typeof document === 'undefined') return null
    
    const value = `; ${document.cookie}`
    const parts = value.split(`; ${name}=`)
    
    if (parts.length === 2) {
      return parts.pop()?.split(';').shift() || null
    }
    
    return null
  }
  
  /**
   * Set a cookie
   */
  export function setCookie(name: string, value: string, days: number = 7): void {
    if (typeof document === 'undefined') return
    
    const expires = new Date()
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000)
    
    document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`
  }
  
  /**
   * Delete a cookie
   */
  export function deleteCookie(name: string): void {
    if (typeof document === 'undefined') return
    
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`
  }
  
  /**
   * Get the JWT access token from session cookie
   */
  export function getAccessToken(): string | null {
    return getCookie('session')
  }
  
  /**
   * Parse JWT without verification (client-side only for reading claims)
   */
  export function parseJWT(token: string): any {
    try {
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      )
      return JSON.parse(jsonPayload)
    } catch (e) {
      return null
    }
  }
  
  /**
   * Get authentication data from JWT token
   */
  export function getAuthData(): { token: string; payload: any } | null {
    const token = getAccessToken()
    if (!token) return null
    
    const payload = parseJWT(token)
    if (!payload) return null
    
    // Check if token is expired
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      clearAuthData()
      return null
    }
    
    return { token, payload }
  }
  
  /**
   * Clear all authentication data
   */
  export function clearAuthData(): void {
    deleteCookie('session')
  }
  
  /**
   * Check if user is authenticated
   */
  export function isAuthenticated(): boolean {
    return getAuthData() !== null
  }