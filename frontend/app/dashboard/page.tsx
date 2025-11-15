"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { DeploymentModal, DeploymentData } from "@/components/DeploymentModal"
import {
  Terminal,
  Layers,
  Settings,
  LogOut,
  FolderGit2,
  Activity,
  Shield,
  Loader2,
  CheckCircle2,
} from "lucide-react"
import { useRouter } from "next/navigation"
import { clearAuthData } from "@/lib/cookies"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

interface Repository {
  id: number
  name: string
  full_name: string
  description: string | null
  private: boolean
  html_url: string
  stargazers_count: number
  forks_count: number
  watchers_count: number
  language: string | null
  updated_at: string
  default_branch: string
}

export default function DashboardPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState("repositories")
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>("")
  const [userData, setUserData] = useState<any>(null)
  const [deploymentModalOpen, setDeploymentModalOpen] = useState(false)
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null)
  const [deploying, setDeploying] = useState(false)
  const [deploySuccess, setDeploySuccess] = useState<string>("")

  useEffect(() => {
    const fetchRepositories = async () => {
      try {
        setLoading(true)

        const res = await fetch(`${API_BASE_URL}/github/repos`, {
            method: "GET",
            credentials: "include", // обязательно
            // НЕ добавляем Authorization: Bearer ... (мы используем cookie)
          })


        if (!res.ok) {
          if (res.status === 401) {
            clearAuthData()
            router.push("/login")
            return
          }
          throw new Error(`Failed to fetch repositories: ${res.status}`)
        }

        const data = await res.json()
        setRepositories(data.repos || data)
        setUserData(data.user || {})
      } catch (e: any) {
        setError(e?.message || "Failed to load repositories")
        // Redirect to login only if we get an authentication error
        if (e?.message?.includes("401") || e?.message?.includes("authentication")) {
          clearAuthData()
          router.push("/login")
        }
      } finally {
        setLoading(false)
      }
    }

    fetchRepositories()
  }, [router])

  const handleLogout = () => {
    clearAuthData()
    router.push("/login")
  }

  const handleDeployClick = (repo: Repository) => {
    setSelectedRepo(repo)
    setDeploymentModalOpen(true)
    setDeploySuccess("")
  }

  const handleDeploy = async (data: DeploymentData) => {
    if (!selectedRepo) return

    setDeploying(true)
    try {
      const res = await fetch(`${API_BASE_URL}/deploy`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          repo_full_name: selectedRepo.full_name,
          folder_path: data.folderPath,
          framework: data.framework,
          secrets: data.secrets,
          user_id: userData?.login || null,
        }),
      })

      if (!res.ok) {
        throw new Error(`Deploy failed: ${res.status}`)
      }

      await res.json()
      setDeploySuccess(
        `✓ ${selectedRepo.name} отправлен на деплой с фреймворком ${data.framework}!`
      )
      setTimeout(() => setDeploySuccess(""), 5000)
    } catch (e: any) {
      setError(e?.message || "Failed to deploy")
    } finally {
      setDeploying(false)
      setDeploymentModalOpen(false)
    }
  }

  const tabs = [
    { id: "repositories", label: "Repositories", icon: FolderGit2 },
    { id: "deployments", label: "Deployments", icon: Layers },
    { id: "activity", label: "Activity", icon: Activity },
    { id: "settings", label: "Settings", icon: Settings },
  ]

  return (
    <div className="relative min-h-screen flex bg-background overflow-hidden">
      {/* Sidebar */}
      <aside className="relative z-10 w-64 border-r border-sidebar-border bg-sidebar/80 backdrop-blur-md flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-sidebar-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/20 rounded-lg border border-primary/30 glow-primary">
              <Terminal className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-bold font-mono text-sidebar-foreground">DevOps Hub</h1>
              <p className="text-xs text-muted-foreground font-mono">Deploy Platform</p>
            </div>
          </div>
        </div>

        {/* User info */}
        {userData && (
          <div className="p-4 border-b border-sidebar-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
                <Shield className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-mono font-semibold text-sidebar-foreground truncate">
                  {userData?.login || "GitHub User"}
                </p>
                <p className="text-xs text-muted-foreground font-mono">Authenticated</p>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg font-mono text-sm transition-all ${
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground border border-primary/30 glow-primary"
                    : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="p-4 border-t border-sidebar-border">
          <Button
            onClick={handleLogout}
            variant="outline"
            className="w-full justify-start gap-3 font-mono border-destructive/30 text-destructive hover:bg-destructive/10"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="relative z-10 flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto p-8">
          <h2 className="text-3xl font-bold font-mono mb-4">
            {tabs.find((t) => t.id === activeTab)?.label}
          </h2>

          {activeTab === "repositories" && (
            <div className="space-y-4">
              {deploySuccess && (
                <Card className="p-4 bg-green-500/10 border-green-500/30">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                    <p className="font-mono text-green-500">{deploySuccess}</p>
                  </div>
                </Card>
              )}

              {loading && (
                <Card className="p-12 bg-card/80 backdrop-blur-md border-primary/30 glow-primary">
                  <div className="flex flex-col items-center justify-center gap-4">
                    <Loader2 className="w-12 h-12 text-primary animate-spin" />
                    <p className="text-lg font-mono text-muted-foreground">Loading repositories...</p>
                  </div>
                </Card>
              )}

              {error && (
                <Card className="p-6 bg-destructive/10 border-destructive/30">
                  <p className="font-mono text-destructive">Error: {error}</p>
                </Card>
              )}

              {!loading && !error && repositories.length > 0 && (
                <div className="grid gap-4">
                  {repositories.map((repo) => (
                    <Card
                      key={repo.id}
                      className="p-6 bg-card/80 border-primary/30 hover:border-primary/50 transition-all"
                    >
                      <div className="flex justify-between">
                        <div>
                          <a
                            href={repo.html_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xl font-bold font-mono text-primary hover:text-primary/80"
                          >
                            {repo.name}
                          </a>
                          <p className="text-sm text-muted-foreground font-mono mt-1">
                            {repo.description || "No description"}
                          </p>
                        </div>
                        <Button
                          size="sm"
                          className="font-mono"
                          onClick={() => handleDeployClick(repo)}
                          disabled={deploying}
                        >
                          {deploying && selectedRepo?.id === repo.id ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Deploying...
                            </>
                          ) : (
                            <>
                              <Layers className="w-4 h-4 mr-2" /> Deploy
                            </>
                          )}
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}

              {!loading && !error && repositories.length === 0 && (
                <Card className="p-12 bg-card/80 backdrop-blur-md border-primary/30">
                  <div className="flex flex-col items-center justify-center gap-4">
                    <FolderGit2 className="w-12 h-12 text-muted-foreground" />
                    <p className="text-lg font-mono text-muted-foreground">No repositories found</p>
                  </div>
                </Card>
              )}
            </div>
          )}

          {activeTab !== "repositories" && (
            <Card className="p-12 bg-card/80 backdrop-blur-md border-primary/30">
              <div className="flex flex-col items-center justify-center gap-4">
                <p className="text-lg font-mono text-muted-foreground">
                  {tabs.find((t) => t.id === activeTab)?.label} coming soon...
                </p>
              </div>
            </Card>
          )}
        </div>
      </main>

      {/* Deployment Modal */}
      {selectedRepo && (
        <DeploymentModal
          open={deploymentModalOpen}
          onOpenChange={setDeploymentModalOpen}
          owner={selectedRepo.full_name.split("/")[0]}
          repo={selectedRepo.full_name.split("/")[1]}
          onDeploy={handleDeploy}
        />
      )}
    </div>
  )
}