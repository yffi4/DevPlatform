"use client"

import { useEffect, useState, useRef } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog"
import { CheckCircle2, AlertCircle, Loader2, ExternalLink } from "lucide-react"
import { Button } from "./ui/button"

const DEPLOYMENT_SERVICE_URL = process.env.DEPLOYMENT_SERVICE_URL || "http://localhost:8003"

interface DeploymentStage {
  stage: string
  status: "pending" | "running" | "success" | "error" | "warning"
  message: string
  progress: number
}

interface DeploymentProgressModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  repoFullName: string
  appName: string
  branch?: string
  port?: number
  domain?: string
  subdirectory?: string
  envVars?: Record<string, string>
}

const STAGE_LABELS: Record<string, string> = {
  validating: "Валидация конфигурации",
  build_setup: "Настройка сборки",
  building: "Сборка Docker образа",
  deploying: "Запуск приложения",
  registering: "Регистрация в Consul",
  routing: "Настройка маршрутизации",
  complete: "Деплой завершён",
  error: "Ошибка деплоя"
}

export function DeploymentProgressModal({
  open,
  onOpenChange,
  repoFullName,
  appName,
  branch = "main",
  port = 8080,
  domain,
  subdirectory,
  envVars = {}
}: DeploymentProgressModalProps) {
  const [stages, setStages] = useState<DeploymentStage[]>([])
  const [isComplete, setIsComplete] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [deployedUrl, setDeployedUrl] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!open) return

    setStages([])
    setIsComplete(false)
    setHasError(false)
    setDeployedUrl(null)

    startDeployment()

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
    }
  }, [open])

  const startDeployment = async () => {
    try {
      const config = {
        repo_full_name: repoFullName,
        app_name: appName,
        branch,
        port,
        domain: domain || `${appName}.localhost`,
        subdirectory: subdirectory || null,
        env_vars: envVars
      }

      const response = await fetch(`${DEPLOYMENT_SERVICE_URL}/api/deploy`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream"
        },
        body: JSON.stringify(config)
      })

      if (!response.ok) {
        throw new Error(`Deployment failed: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error("No response body")
      }

      let buffer = ""
      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split("\n\n")
        buffer = lines.pop() || ""

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.substring(6)
            try {
              const event = JSON.parse(data)
              handleDeploymentEvent(event)
            } catch (e) {
              console.error("Failed to parse SSE data:", data, e)
            }
          }
        }
      }
    } catch (error) {
      console.error("Deployment error:", error)
      setStages(prev => [...prev, {
        stage: "error",
        status: "error",
        message: `Ошибка подключения: ${error instanceof Error ? error.message : "Unknown error"}`,
        progress: 0
      }])
      setHasError(true)
    }
  }

  const handleDeploymentEvent = (event: DeploymentStage) => {
    setStages(prev => {
      const existingIndex = prev.findIndex(s => s.stage === event.stage)
      if (existingIndex >= 0) {
        const updated = [...prev]
        updated[existingIndex] = event
        return updated
      } else {
        return [...prev, event]
      }
    })

    if (event.stage === "complete" && event.status === "success") {
      setIsComplete(true)
      const urlMatch = event.message.match(/http:\/\/[^\s]+/)
      if (urlMatch) {
        setDeployedUrl(urlMatch[0])
      }
    } else if (event.status === "error") {
      setHasError(true)
    }
  }

  const getStatusIcon = (status: DeploymentStage["status"]) => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case "running":
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      case "error":
        return <AlertCircle className="w-5 h-5 text-red-500" />
      case "warning":
        return <AlertCircle className="w-5 h-5 text-yellow-500" />
      default:
        return <div className="w-5 h-5 rounded-full border-2 border-muted-foreground/30" />
    }
  }

  const getStatusColor = (status: DeploymentStage["status"]) => {
    switch (status) {
      case "success":
        return "text-green-500"
      case "running":
        return "text-blue-500"
      case "error":
        return "text-red-500"
      case "warning":
        return "text-yellow-500"
      default:
        return "text-muted-foreground"
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isComplete ? "✓ Деплой завершён успешно!" : hasError ? "✗ Ошибка деплоя" : "Деплой приложения..."}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${hasError ? "bg-red-500" : isComplete ? "bg-green-500" : "bg-blue-500"}`}
              style={{ width: `${stages[stages.length - 1]?.progress || 0}%` }}
            />
          </div>

          <div className="space-y-3 max-h-[400px] overflow-y-auto">
            {stages.map((stage, index) => (
              <div
                key={`${stage.stage}-${index}`}
                className={`p-4 rounded-lg border transition-all ${
                  stage.status === "error"
                    ? "bg-red-500/10 border-red-500/30"
                    : stage.status === "success"
                    ? "bg-green-500/10 border-green-500/30"
                    : stage.status === "running"
                    ? "bg-blue-500/10 border-blue-500/30"
                    : "bg-muted/50 border-muted"
                }`}
              >
                <div className="flex items-start gap-3">
                  {getStatusIcon(stage.status)}
                  <div className="flex-1 min-w-0">
                    <p className={`font-mono text-sm font-semibold ${getStatusColor(stage.status)}`}>
                      {STAGE_LABELS[stage.stage] || stage.stage}
                    </p>
                    <p className="font-mono text-xs text-muted-foreground mt-1 break-words">
                      {stage.message}
                    </p>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground">
                    {stage.progress}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          {isComplete && deployedUrl && (
            <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
              <p className="font-mono text-sm text-green-500 mb-2">
                Ваше приложение успешно развёрнуто!
              </p>
              <a
                href={deployedUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm font-mono text-primary hover:underline"
              >
                {deployedUrl}
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          )}

          {(isComplete || hasError) && (
            <div className="flex justify-end pt-4">
              <Button onClick={() => onOpenChange(false)}>
                Закрыть
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
