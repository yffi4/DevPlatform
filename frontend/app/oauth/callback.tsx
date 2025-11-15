"use client"

import { useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Loader2, AlertCircle } from "lucide-react"
import { Card } from "@/components/ui/card"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

export default function CallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [error, setError] = useState<string>("")

  useEffect(() => {
    const code = searchParams.get("code")
    if (!code) {
      router.push("/login")
      return
    }
    // Перенаправляем браузер напрямую на бэкенд — чтобы он выставил cookie и сам редиректнул на /dashboard
    window.location.href = `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/github/callback?code=${code}`
  }, [searchParams, router])

  
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md p-8 bg-card/80 backdrop-blur-md border-primary/30">
        <div className="flex flex-col items-center justify-center gap-6">
          {error ? (
            <>
              <AlertCircle className="w-16 h-16 text-destructive" />
              <div className="text-center">
                <h2 className="text-2xl font-bold font-mono text-destructive mb-2">
                  Authentication Failed
                </h2>
                <p className="text-muted-foreground font-mono">{error}</p>
                <p className="text-sm text-muted-foreground font-mono mt-4">
                  Redirecting to login...
                </p>
              </div>
            </>
          ) : (
            <>
              <Loader2 className="w-16 h-16 text-primary animate-spin" />
              <div className="text-center">
                <h2 className="text-2xl font-bold font-mono text-foreground mb-2">
                  Authenticating...
                </h2>
                <p className="text-muted-foreground font-mono">
                  Please wait while we complete your login
                </p>
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
  )
}