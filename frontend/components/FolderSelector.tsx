"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogBody, DialogFooter } from "./ui/dialog"
import { Button } from "./ui/button"
import { Folder, ChevronRight, Home, Loader2 } from "lucide-react"

const API_BASE_URL = process.env.PROJECT_SERVICE_URL|| "http://localhost:8001"

interface FileItem {
  name: string
  path: string
  type: "file" | "dir"
  sha: string
}

interface FolderSelectorProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  owner: string
  repo: string
  onSelect: (folderPath: string) => void
}

export function FolderSelector({ open, onOpenChange, owner, repo, onSelect }: FolderSelectorProps) {
  const [currentPath, setCurrentPath] = useState("")
  const [contents, setContents] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [breadcrumbs, setBreadcrumbs] = useState<string[]>([])

  useEffect(() => {
    if (open) {
      loadContents("")
    }
  }, [open, owner, repo])

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

  const handleSelect = () => {
    onSelect(currentPath)
    onOpenChange(false)
  }

  const folders = contents.filter((item) => item.type === "dir")

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>Выберите папку для деплоя</DialogTitle>
        </DialogHeader>

        <DialogBody>
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 mb-4 text-sm font-mono">
            <button
              onClick={() => handleBreadcrumbClick(-1)}
              className="flex items-center gap-1 text-primary hover:text-primary/80 transition-colors"
            >
              <Home className="w-4 h-4" />
              <span>{owner}/{repo}</span>
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
            <p className="font-mono text-primary">
              {currentPath || "/" }
            </p>
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
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button onClick={handleSelect}>
            Выбрать эту папку
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
