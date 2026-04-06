"use client"

import { useState, useCallback } from "react"
import { Sidebar, MobileSidebar } from "./sidebar"
import { Header } from "./header"
import { cn } from "@/lib/utils"

interface ShellProps {
  children: React.ReactNode
  className?: string
}

export function Shell({ children, className }: ShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev)
  }, [])

  const openMobileMenu = useCallback(() => {
    setMobileMenuOpen(true)
  }, [])

  const closeMobileMenu = useCallback(() => {
    setMobileMenuOpen(false)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={toggleSidebar}
        className="hidden lg:flex"
      />

      {/* Mobile Sidebar */}
      <MobileSidebar open={mobileMenuOpen} onClose={closeMobileMenu} />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header onMenuClick={openMobileMenu} />

        <main
          className={cn(
            "flex-1 overflow-y-auto bg-muted/30 p-4 md:p-6",
            className
          )}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
