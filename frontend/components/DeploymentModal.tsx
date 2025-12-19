"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogBody, DialogFooter } from "./ui/dialog"
import { Button } from "./ui/button"
import { Card } from "./ui/card"
import { DeploymentProgressModal } from "./DeploymentProgressModal"
import {
  Folder,
  ChevronRight,
  Home,
  Loader2,
  Sparkles,
  Settings2,
  Plus,
  X,
  CheckCircle2,
  AlertCircle,
  Upload,
  FileText,
  Shield,
  Rocket,
} from "lucide-react"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
const PROJECT_SERVICE_URL = process.env.PROJECT_SERVICE_URL|| "http://localhost:8001"
const SECRET_MANAGER_URL = process.env.SECRET_MANAGER_URL || "http://localhost:8002"

interface FileItem {
  name: string
  path: string
  type: "file" | "dir"
  sha: string
}

interface DeploymentModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  owner: string
  repo: string
}

export interface DeploymentData {
  folderPath: string
  framework: string
  secrets: Record<string, string>
}

interface Secret {
  key: string
  value: string
}

export function DeploymentModal({ open, onOpenChange, owner, repo }: DeploymentModalProps) {
  // Folder selection state
  const [currentPath, setCurrentPath] = useState("")
  const [contents, setContents] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [breadcrumbs, setBreadcrumbs] = useState<string[]>([])

  // Framework detection state
  const [frameworks, setFrameworks] = useState<string[]>([])
  const [detectedFramework, setDetectedFramework] = useState<string | null>(null)
  const [selectedFramework, setSelectedFramework] = useState<string>("")
  const [detectingFramework, setDetectingFramework] = useState(false)
  const [frameworkError, setFrameworkError] = useState("")

  // Secrets state
  const [secrets, setSecrets] = useState<Secret[]>([])
  const [showSecretForm, setShowSecretForm] = useState(false)
  const [newSecretKey, setNewSecretKey] = useState("")
  const [newSecretValue, setNewSecretValue] = useState("")
  const [envFileText, setEnvFileText] = useState("")
  const [showEnvTextArea, setShowEnvTextArea] = useState(false)
  const [secretsSaved, setSecretsSaved] = useState(false)
  const [savingSecrets, setSavingSecrets] = useState(false)
  const [secretsError, setSecretsError] = useState("")

  // Current step
  const [step, setStep] = useState<1 | 2 | 3>(1)

  // Progress modal
  const [showProgressModal, setShowProgressModal] = useState(false)

  useEffect(() => {
    if (open) {
      loadContents("")
      loadFrameworks()
      resetState()
    }
  }, [open, owner, repo])

  const resetState = () => {
    setStep(1)
    setCurrentPath("")
    setDetectedFramework(null)
    setSelectedFramework("")
    setSecrets([])
    setError("")
    setFrameworkError("")
    setSecretsSaved(false)
    setSecretsError("")
  }

  const loadFrameworks = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/frameworks`, {
        method: "GET",
        credentials: "include",
      })

      if (res.ok) {
        const data = await res.json()
        setFrameworks(data.frameworks || [])
      }
    } catch (e) {
      console.error("Failed to load frameworks:", e)
    }
  }

  const loadContents = async (path: string) => {
    setLoading(true)
    setError("")

    try {
      const url = `${API_BASE_URL}/github/repo/${owner}/${repo}/contents?path=${encodeURIComponent(path)}`
      const res = await fetch(url, {
        method: "GET",
        credentials: "include",
      })

      if (!res.ok) {
        throw new Error(`Failed to load contents: ${res.status}`)
      }

      const data = await res.json()
      setContents(data.contents || [])
      setCurrentPath(path)

      // Update breadcrumbs
      if (path) {
        setBreadcrumbs(path.split("/").filter(Boolean))
      } else {
        setBreadcrumbs([])
      }
    } catch (e: any) {
      setError(e?.message || "Failed to load folder contents")
    } finally {
      setLoading(false)
    }
  }

  const detectFramework = async (folderPath: string) => {
    setDetectingFramework(true)
    setFrameworkError("")

    try {
      const res = await fetch(`${PROJECT_SERVICE_URL}/detect-framework`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          project_id: `${owner}/${repo}`,
          repo_full_name: `${owner}/${repo}`,
          folder_path: folderPath,
        }),
      })

      if (!res.ok) {
        throw new Error(`Failed to detect framework: ${res.status}`)
      }

      const data = await res.json()
      if (data.primary_framework) {
        setDetectedFramework(data.primary_framework)
        setSelectedFramework(data.primary_framework)
      } else {
        setFrameworkError("Не удалось автоматически определить фреймворк. Пожалуйста, выберите вручную.")
      }
    } catch (e: any) {
      setFrameworkError(e?.message || "Failed to detect framework")
    } finally {
      setDetectingFramework(false)
    }
  }

  const handleFolderClick = (folder: FileItem) => {
    if (folder.type === "dir") {
      loadContents(folder.path)
    }
  }

  const handleBreadcrumbClick = (index: number) => {
    if (index === -1) {
      loadContents("")
    } else {
      const newPath = breadcrumbs.slice(0, index + 1).join("/")
      loadContents(newPath)
    }
  }

  const handleStepNext = () => {
    if (step === 1) {
      setStep(2)
      detectFramework(currentPath)
    } else if (step === 2) {
      setStep(3)
    }
  }

  const handleStepBack = () => {
    if (step === 2) {
      setStep(1)
    } else if (step === 3) {
      setStep(2)
    }
  }

  const handleAddSecret = () => {
    if (newSecretKey.trim() && newSecretValue.trim()) {
      setSecrets([...secrets, { key: newSecretKey.trim(), value: newSecretValue.trim() }])
      setNewSecretKey("")
      setNewSecretValue("")
      setShowSecretForm(false)
    }
  }

  const handleRemoveSecret = (index: number) => {
    setSecrets(secrets.filter((_, i) => i !== index))
  }

  const parseEnvFile = (content: string): Secret[] => {
    const lines = content.split('\n')
    const parsedSecrets: Secret[] = []

    lines.forEach((line) => {
      // Skip empty lines and comments
      const trimmedLine = line.trim()
      if (!trimmedLine || trimmedLine.startsWith('#')) {
        return
      }

      // Parse KEY=VALUE format
      const equalIndex = trimmedLine.indexOf('=')
      if (equalIndex > 0) {
        const key = trimmedLine.substring(0, equalIndex).trim()
        let value = trimmedLine.substring(equalIndex + 1).trim()

        // Remove quotes if present
        if ((value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))) {
          value = value.substring(1, value.length - 1)
        }

        if (key) {
          parsedSecrets.push({ key, value })
        }
      }
    })

    return parsedSecrets
  }

  const handleEnvFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        const content = e.target?.result as string
        const parsedSecrets = parseEnvFile(content)

        // Merge with existing secrets, avoiding duplicates
        const existingKeys = new Set(secrets.map(s => s.key))
        const newSecrets = parsedSecrets.filter(s => !existingKeys.has(s.key))
        setSecrets([...secrets, ...newSecrets])
      }
      reader.readAsText(file)
      // Reset input
      event.target.value = ''
    }
  }

  const handleEnvTextSubmit = () => {
    if (envFileText.trim()) {
      const parsedSecrets = parseEnvFile(envFileText)

      // Merge with existing secrets, avoiding duplicates
      const existingKeys = new Set(secrets.map(s => s.key))
      const newSecrets = parsedSecrets.filter(s => !existingKeys.has(s.key))
      setSecrets([...secrets, ...newSecrets])

      setEnvFileText("")
      setShowEnvTextArea(false)
    }
  }

  const handleSaveSecrets = async () => {
    if (secrets.length === 0) {
      setSecretsError("Добавьте хотя бы один секрет перед сохранением")
      return
    }

    setSavingSecrets(true)
    setSecretsError("")

    try {
      const secretsObj: Record<string, string> = {}
      secrets.forEach((secret) => {
        secretsObj[secret.key] = secret.value
      })

      const projectId = `${owner}/${repo}`

      const res = await fetch(`${SECRET_MANAGER_URL}/secrets`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          project_id: projectId,
          secrets: secretsObj,
        }),
      })

      if (!res.ok) {
        throw new Error(`Failed to save secrets: ${res.status}`)
      }

      setSecretsSaved(true)
    } catch (e: any) {
      setSecretsError(e?.message || "Failed to save secrets")
    } finally {
      setSavingSecrets(false)
    }
  }

  const handleDeploy = () => {
    // Close config modal and open progress modal
    onOpenChange(false)
    setShowProgressModal(true)
  }

  const folders = contents.filter((item) => item.type === "dir")

  // Build env vars object
  const envVarsObj: Record<string, string> = {}
  secrets.forEach((secret) => {
    envVarsObj[secret.key] = secret.value
  })

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>
            {step === 1 && "Шаг 1: Выберите папку для деплоя"}
            {step === 2 && "Шаг 2: Выберите фреймворк"}
            {step === 3 && "Шаг 3: Добавьте секреты (опционально)"}
          </DialogTitle>
        </DialogHeader>

        <DialogBody>
          {/* Step 1: Folder Selection */}
          {step === 1 && (
            <>
              {/* Breadcrumbs */}
              <div className="flex items-center gap-2 mb-4 text-sm font-mono">
                <button
                  onClick={() => handleBreadcrumbClick(-1)}
                  className="flex items-center gap-1 text-primary hover:text-primary/80 transition-colors"
                >
                  <Home className="w-4 h-4" />
                  <span>
                    {owner}/{repo}
                  </span>
                </button>
                {breadcrumbs.map((crumb, index) => (
                  <div key={index} className="flex items-center gap-1">
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    <button
                      onClick={() => handleBreadcrumbClick(index)}
                      className="text-primary hover:text-primary/80 transition-colors"
                    >
                      {crumb}
                    </button>
                  </div>
                ))}
              </div>

              {/* Current path display */}
              <div className="mb-4 p-3 bg-sidebar/50 rounded-lg border border-primary/20">
                <p className="text-sm font-mono text-muted-foreground">Текущая папка:</p>
                <p className="font-mono text-primary">{currentPath || "/"}</p>
              </div>

              {/* Folder list */}
              {loading && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-primary animate-spin" />
                </div>
              )}

              {error && (
                <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
                  <p className="text-destructive font-mono">{error}</p>
                </div>
              )}

              {!loading && !error && folders.length === 0 && (
                <div className="py-12 text-center">
                  <p className="text-muted-foreground font-mono">Нет подпапок в этой директории</p>
                </div>
              )}

              {!loading && !error && folders.length > 0 && (
                <div className="space-y-2">
                  {folders.map((folder) => (
                    <button
                      key={folder.sha}
                      onClick={() => handleFolderClick(folder)}
                      className="w-full flex items-center gap-3 p-3 rounded-lg border border-primary/20 hover:border-primary/40 hover:bg-sidebar/30 transition-all text-left"
                    >
                      <Folder className="w-5 h-5 text-primary" />
                      <span className="font-mono">{folder.name}</span>
                      <ChevronRight className="w-4 h-4 ml-auto text-muted-foreground" />
                    </button>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Step 2: Framework Selection */}
          {step === 2 && (
            <div className="space-y-4">
              {/* Auto-detection result */}
              {detectingFramework && (
                <Card className="p-4 bg-sidebar/50 border-primary/20">
                  <div className="flex items-center gap-3">
                    <Loader2 className="w-5 h-5 text-primary animate-spin" />
                    <div>
                      <p className="font-mono text-sm text-primary">Автоопределение фреймворка...</p>
                      <p className="font-mono text-xs text-muted-foreground">Анализируем структуру проекта</p>
                    </div>
                  </div>
                </Card>
              )}

              {detectedFramework && !detectingFramework && (
                <Card className="p-4 bg-green-500/10 border-green-500/30">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                    <div>
                      <p className="font-mono text-sm text-green-500">Фреймворк определён автоматически</p>
                      <p className="font-mono text-lg font-bold text-green-400">{detectedFramework}</p>
                    </div>
                  </div>
                </Card>
              )}

              {frameworkError && !detectingFramework && (
                <Card className="p-4 bg-yellow-500/10 border-yellow-500/30">
                  <div className="flex items-center gap-3">
                    <AlertCircle className="w-5 h-5 text-yellow-500" />
                    <p className="font-mono text-sm text-yellow-500">{frameworkError}</p>
                  </div>
                </Card>
              )}

              {/* Manual framework selection */}
              <div>
                <label className="block text-sm font-mono font-semibold mb-2">
                  Выберите фреймворк {detectedFramework && "(или измените выбор)"}:
                </label>
                <select
                  value={selectedFramework}
                  onChange={(e) => setSelectedFramework(e.target.value)}
                  className="w-full p-3 bg-sidebar/50 border border-primary/20 rounded-lg font-mono text-sm focus:outline-none focus:border-primary/50 transition-colors"
                >
                  <option value="">-- Выберите фреймворк --</option>
                  {frameworks.map((framework) => (
                    <option key={framework} value={framework}>
                      {framework}
                    </option>
                  ))}
                </select>
              </div>

              {/* Selected path info */}
              <Card className="p-4 bg-sidebar/50 border-primary/20">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Folder className="w-4 h-4 text-primary" />
                    <p className="text-sm font-mono text-muted-foreground">Папка для деплоя:</p>
                  </div>
                  <p className="font-mono text-primary">{currentPath || "/"}</p>
                </div>
              </Card>
            </div>
          )}

          {/* Step 3: Secrets Management */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="p-4 bg-sidebar/50 border border-primary/20 rounded-lg">
                <p className="text-sm font-mono text-muted-foreground mb-2">
                  Добавьте переменные окружения (секреты) для вашего приложения:
                </p>
                <p className="text-xs font-mono text-muted-foreground">
                  Например: DATABASE_URL, API_KEY, SECRET_TOKEN и т.д.
                </p>
              </div>

              {/* Secrets list */}
              {secrets.length > 0 && (
                <div className="space-y-2">
                  {secrets.map((secret, index) => (
                    <Card key={index} className="p-3 bg-card/80 border-primary/20">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="font-mono text-sm font-semibold text-primary">{secret.key}</p>
                          <p className="font-mono text-xs text-muted-foreground">
                            {secret.value.substring(0, 20)}
                            {secret.value.length > 20 ? "..." : ""}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => handleRemoveSecret(index)}
                          className="text-destructive hover:text-destructive/80"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}

              {/* Add secret form */}
              {!showSecretForm && !showEnvTextArea && (
                <div className="grid grid-cols-2 gap-3">
                  <Button
                    onClick={() => setShowSecretForm(true)}
                    variant="outline"
                    className="border-primary/30 hover:border-primary/50"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Добавить секрет
                  </Button>

                  <label className="cursor-pointer">
                    <input
                      type="file"
                      accept=".env"
                      onChange={handleEnvFileUpload}
                      className="hidden"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full border-primary/30 hover:border-primary/50"
                      onClick={(e) => {
                        e.preventDefault()
                        e.currentTarget.parentElement?.querySelector('input')?.click()
                      }}
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Загрузить .env
                    </Button>
                  </label>

                  <Button
                    onClick={() => setShowEnvTextArea(true)}
                    variant="outline"
                    className="col-span-2 border-primary/30 hover:border-primary/50"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    Вставить текст .env
                  </Button>
                </div>
              )}

              {showSecretForm && (
                <Card className="p-4 bg-sidebar/50 border-primary/30">
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-mono font-semibold mb-1">Ключ:</label>
                      <input
                        type="text"
                        value={newSecretKey}
                        onChange={(e) => setNewSecretKey(e.target.value)}
                        placeholder="DATABASE_URL"
                        className="w-full p-2 bg-background border border-primary/20 rounded font-mono text-sm focus:outline-none focus:border-primary/50"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-mono font-semibold mb-1">Значение:</label>
                      <input
                        type="password"
                        value={newSecretValue}
                        onChange={(e) => setNewSecretValue(e.target.value)}
                        placeholder="postgresql://..."
                        className="w-full p-2 bg-background border border-primary/20 rounded font-mono text-sm focus:outline-none focus:border-primary/50"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={handleAddSecret} size="sm" className="flex-1">
                        Добавить
                      </Button>
                      <Button
                        onClick={() => {
                          setShowSecretForm(false)
                          setNewSecretKey("")
                          setNewSecretValue("")
                        }}
                        variant="outline"
                        size="sm"
                        className="flex-1"
                      >
                        Отмена
                      </Button>
                    </div>
                  </div>
                </Card>
              )}

              {showEnvTextArea && (
                <Card className="p-4 bg-sidebar/50 border-primary/30">
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-mono font-semibold mb-1">
                        Вставьте содержимое .env файла:
                      </label>
                      <textarea
                        value={envFileText}
                        onChange={(e) => setEnvFileText(e.target.value)}
                        placeholder="DATABASE_URL=postgresql://...&#10;API_KEY=your_key_here&#10;SECRET_TOKEN=your_token"
                        rows={8}
                        className="w-full p-2 bg-background border border-primary/20 rounded font-mono text-sm focus:outline-none focus:border-primary/50 resize-none"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Формат: KEY=VALUE (по одной паре на строку)
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={handleEnvTextSubmit} size="sm" className="flex-1">
                        Импортировать
                      </Button>
                      <Button
                        onClick={() => {
                          setShowEnvTextArea(false)
                          setEnvFileText("")
                        }}
                        variant="outline"
                        size="sm"
                        className="flex-1"
                      >
                        Отмена
                      </Button>
                    </div>
                  </div>
                </Card>
              )}

              {/* Secrets status messages */}
              {secretsError && (
                <Card className="p-4 bg-destructive/10 border-destructive/30">
                  <div className="flex items-center gap-3">
                    <AlertCircle className="w-5 h-5 text-destructive" />
                    <p className="font-mono text-sm text-destructive">{secretsError}</p>
                  </div>
                </Card>
              )}

              {secretsSaved && (
                <Card className="p-4 bg-green-500/10 border-green-500/30">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                    <p className="font-mono text-sm text-green-500">
                      Секреты успешно сохранены! Теперь можно запустить деплой.
                    </p>
                  </div>
                </Card>
              )}

              {/* Summary */}
              <Card className="p-4 bg-sidebar/50 border-primary/20">
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-mono text-muted-foreground mb-1">Папка:</p>
                    <p className="font-mono text-sm text-primary">{currentPath || "/"}</p>
                  </div>
                  <div>
                    <p className="text-xs font-mono text-muted-foreground mb-1">Фреймворк:</p>
                    <p className="font-mono text-sm text-primary">{selectedFramework}</p>
                  </div>
                  <div>
                    <p className="text-xs font-mono text-muted-foreground mb-1">Секретов добавлено:</p>
                    <p className="font-mono text-sm text-primary">{secrets.length}</p>
                  </div>
                  <div>
                    <p className="text-xs font-mono text-muted-foreground mb-1">Статус секретов:</p>
                    <p className="font-mono text-sm text-primary">
                      {secretsSaved ? "✓ Сохранены" : "Не сохранены"}
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          )}
        </DialogBody>

        <DialogFooter>
          {step > 1 && (
            <Button variant="outline" onClick={handleStepBack}>
              Назад
            </Button>
          )}

          {step === 1 && (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Отмена
              </Button>
              <Button onClick={handleStepNext}>
                <Sparkles className="w-4 h-4 mr-2" />
                Далее: Выбор фреймворка
              </Button>
            </>
          )}

          {step === 2 && (
            <Button onClick={handleStepNext} disabled={!selectedFramework}>
              <Settings2 className="w-4 h-4 mr-2" />
              Далее: Добавить секреты
            </Button>
          )}

          {step === 3 && (
            <>
              {!secretsSaved ? (
                <Button
                  onClick={handleSaveSecrets}
                  disabled={!selectedFramework || secrets.length === 0 || savingSecrets}
                >
                  {savingSecrets ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Сохранение...
                    </>
                  ) : (
                    <>
                      <Shield className="w-4 h-4 mr-2" />
                      Сохранить секреты
                    </>
                  )}
                </Button>
              ) : (
                <Button onClick={handleDeploy} disabled={!selectedFramework}>
                  <Rocket className="w-4 h-4 mr-2" />
                  Запустить Деплой
                </Button>
              )}
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <DeploymentProgressModal
      open={showProgressModal}
      onOpenChange={setShowProgressModal}
      repoFullName={`${owner}/${repo}`}
      appName={repo}
      branch="main"
      port={8080}
      subdirectory={currentPath || undefined}
      envVars={envVarsObj}
    />
    </>
  )
}
