import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // IMPORTANT: Use getUser(), not getSession(). getUser() validates the JWT.
  const {
    data: { user },
  } = await supabase.auth.getUser()

  const path = request.nextUrl.pathname

  // Public routes (no auth required)
  const publicRoutes = ['/', '/login', '/signup', '/product', '/policy', '/docs']
  const isPublicRoute = publicRoutes.includes(path)

  // Not authenticated + protected route → login
  if (!user && !isPublicRoute) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  // Authenticated + landing page → dashboard
  if (user && path === '/') {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  // Authenticated + login/signup → dashboard
  if (user && (path === '/login' || path === '/signup')) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  // Authenticated + dashboard → check if onboarding is complete
  if (user && path === '/dashboard') {
    try {
      const session = (await supabase.auth.getSession()).data.session
      if (session) {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_FLASK_API_URL}/api/auth/me`,
          { headers: { Authorization: `Bearer ${session.access_token}` } }
        )
        if (res.status === 404) {
          const url = request.nextUrl.clone()
          url.pathname = '/onboarding'
          return NextResponse.redirect(url)
        }
      }
    } catch {
      // Flask might be down — let dashboard handle the error
    }
  }

  // IMPORTANT: Return supabaseResponse, not NextResponse.next()
  // The supabaseResponse has updated cookies from session refresh.
  return supabaseResponse
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
