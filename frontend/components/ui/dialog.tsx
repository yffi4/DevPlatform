import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "./button"

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

function Dialog({ open, onOpenChange, children }: DialogProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />

      {/* Dialog content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  )
}

interface DialogContentProps extends React.ComponentProps<"div"> {
  onClose?: () => void
}

function DialogContent({ className, onClose, children, ...props }: DialogContentProps) {
  return (
    <div
      className={cn(
        "relative bg-card border border-primary/30 rounded-lg shadow-lg w-full max-w-2xl max-h-[80vh] overflow-hidden",
        className
      )}
      {...props}
    >
      {onClose && (
        <Button
          variant="ghost"
          size="icon-sm"
          className="absolute right-4 top-4 z-10"
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
      )}
      {children}
    </div>
  )
}

function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn("px-6 py-4 border-b border-primary/30", className)}
      {...props}
    />
  )
}

function DialogTitle({ className, ...props }: React.ComponentProps<"h2">) {
  return (
    <h2
      className={cn("text-xl font-bold font-mono", className)}
      {...props}
    />
  )
}

function DialogBody({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn("px-6 py-4 overflow-y-auto max-h-[60vh]", className)}
      {...props}
    />
  )
}

function DialogFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn("px-6 py-4 border-t border-primary/30 flex justify-end gap-2", className)}
      {...props}
    />
  )
}

export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogBody, DialogFooter }
