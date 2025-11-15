"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Terminal, Lock, Shield, Server, GitBranch, Zap } from "lucide-react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function LoginPage() {
  const [terminalText, setTerminalText] = useState("");
  const [showCursor, setShowCursor] = useState(true);

  const fullText = "$ Initializing secure authentication protocol...";

  useEffect(() => {
    let index = 0;
    const timer = setInterval(() => {
      if (index <= fullText.length) {
        setTerminalText(fullText.slice(0, index));
        index++;
      } else {
        clearInterval(timer);
      }
    }, 50);

    const cursorTimer = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 500);

    return () => {
      clearInterval(timer);
      clearInterval(cursorTimer);
    };
  }, []);

  const handleLogin = () => {
    window.location.href = `${API_BASE_URL}/github/login`;
  };

  return (
    <main className="relative min-h-screen flex items-center justify-center overflow-hidden bg-background">
      {/* Grid background pattern */}
      <div className="absolute inset-0 grid-pattern opacity-30" />

      {/* Animated scan line */}
      <div className="scan-line absolute inset-0 pointer-events-none" />

      {/* Floating particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-primary/30 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `float ${5 + Math.random() * 10}s linear infinite`,
              animationDelay: `${Math.random() * 5}s`,
            }}
          />
        ))}
      </div>

      <style jsx>{`
        @keyframes float {
          0% {
            transform: translateY(0) translateX(0);
            opacity: 0;
          }
          10% {
            opacity: 0.3;
          }
          90% {
            opacity: 0.3;
          }
          100% {
            transform: translateY(-100vh)
              translateX(${Math.random() * 100 - 50}px);
            opacity: 0;
          }
        }
      `}</style>

      <div className="relative z-10 w-full max-w-6xl mx-auto px-4">
        <div className="grid lg:grid-cols-2 gap-8 items-center">
          {/* Left side - Info */}
          <div className="space-y-6">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-3 bg-primary/10 rounded-lg border border-primary/30 glow-primary">
                <Server className="w-8 h-8 text-primary" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-glow font-mono">
                  DevOps Platform
                </h1>
                <p className="text-sm text-muted-foreground font-mono">
                  v2.4.1-secure
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-start gap-3 p-4 bg-card/50 border border-border/50 rounded-lg backdrop-blur-sm">
                <Shield className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-foreground mb-1">
                    Enterprise Security
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Military-grade encryption with OAuth 2.0 authentication
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 bg-card/50 border border-border/50 rounded-lg backdrop-blur-sm">
                <Zap className="w-5 h-5 text-accent mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-foreground mb-1">
                    Lightning Fast Deployments
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Deploy in seconds with automated CI/CD pipelines
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 bg-card/50 border border-border/50 rounded-lg backdrop-blur-sm">
                <GitBranch className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-foreground mb-1">
                    GitHub Integration
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Seamless integration with your repositories
                  </p>
                </div>
              </div>
            </div>

            {/* Terminal output */}
            <div className="mt-8 p-4 bg-black/40 border border-primary/30 rounded-lg font-mono text-sm">
              <div className="flex items-center gap-2 mb-2 text-primary">
                <Terminal className="w-4 h-4" />
                <span>system.log</span>
              </div>
              <div className="text-primary/80">
                {terminalText}
                {showCursor && (
                  <span className="inline-block w-2 h-4 bg-primary ml-1 animate-pulse" />
                )}
              </div>
            </div>
          </div>

          {/* Right side - Login Card */}
          <div className="flex justify-center lg:justify-end">
            <Card className="w-full max-w-md p-8 bg-card/80 backdrop-blur-md border-primary/30 glow-primary">
              <div className="space-y-6">
                <div className="text-center space-y-2">
                  <div className="inline-flex p-4 bg-primary/10 rounded-full border border-primary/30 mb-4">
                    <Lock className="w-8 h-8 text-primary" />
                  </div>
                  <h2 className="text-2xl font-bold text-foreground font-mono">
                    Secure Access
                  </h2>
                  <p className="text-muted-foreground text-sm">
                    Authenticate with your GitHub account to continue
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="p-4 bg-muted/50 border border-border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono text-muted-foreground">
                        STATUS
                      </span>
                      <span className="flex items-center gap-1.5 text-xs font-mono text-primary">
                        <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
                        READY
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-muted-foreground">
                        PROTOCOL
                      </span>
                      <span className="text-xs font-mono text-foreground">
                        OAuth 2.0
                      </span>
                    </div>
                  </div>

                  <Button
                    onClick={handleLogin}
                    className="w-full h-12 bg-primary hover:bg-primary/90 text-primary-foreground font-mono font-semibold text-base glow-primary transition-all duration-300 hover:scale-[1.02]"
                  >
                    <GitBranch className="w-5 h-5 mr-2" />
                    Continue with GitHub
                  </Button>

                  <div className="pt-4 border-t border-border/50">
                    <p className="text-xs text-center text-muted-foreground font-mono">
                      Protected by end-to-end encryption
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Bottom stats */}
        <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Uptime", value: "99.99%" },
            { label: "Deployments", value: "1M+" },
            { label: "Response Time", value: "<50ms" },
            { label: "Security Score", value: "A+" },
          ].map((stat, i) => (
            <div
              key={i}
              className="p-4 bg-card/30 border border-border/30 rounded-lg backdrop-blur-sm text-center"
            >
              <div className="text-2xl font-bold text-primary font-mono">
                {stat.value}
              </div>
              <div className="text-xs text-muted-foreground font-mono mt-1">
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
