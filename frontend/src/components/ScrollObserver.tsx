"use client"

import React, { createContext, useContext, useRef, useEffect, useState, ReactNode } from 'react'

interface ScrollObserverContextType {
  registerTrigger: (id: string, element: HTMLElement) => void
  unregisterTrigger: (id: string) => void
  registerReactor: (id: string, element: HTMLElement) => void
  unregisterReactor: (id: string) => void
  activeTrigger: string | null
}

const ScrollObserverContext = createContext<ScrollObserverContextType | null>(null)

export function ScrollObserver({ 
  children, 
  className 
}: { 
  children: (isHidden: boolean) => ReactNode
  className?: string 
}) {
  const [activeTrigger, setActiveTrigger] = useState<string | null>(null)
  const [isHidden, setIsHidden] = useState(false)
  const triggersRef = useRef<Map<string, HTMLElement>>(new Map())
  const reactorsRef = useRef<Map<string, HTMLElement>>(new Map())

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY
      const windowHeight = window.innerHeight
      const centerY = scrollY + windowHeight / 2

      let closestId: string | null = null
      let closestDistance = Infinity

      triggersRef.current.forEach((element, id) => {
        const rect = element.getBoundingClientRect()
        const elementCenter = rect.top + rect.height / 2 + scrollY
        const distance = Math.abs(elementCenter - centerY)
        
        if (distance < closestDistance) {
          closestDistance = distance
          closestId = id
        }
      })

      setActiveTrigger(closestId)
      setIsHidden(scrollY > 100)
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll() // Initial call

    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const registerTrigger = (id: string, element: HTMLElement) => {
    triggersRef.current.set(id, element)
  }

  const unregisterTrigger = (id: string) => {
    triggersRef.current.delete(id)
  }

  const registerReactor = (id: string, element: HTMLElement) => {
    reactorsRef.current.set(id, element)
  }

  const unregisterReactor = (id: string) => {
    reactorsRef.current.delete(id)
  }

  return (
    <ScrollObserverContext.Provider value={{
      registerTrigger,
      unregisterTrigger,
      registerReactor,
      unregisterReactor,
      activeTrigger
    }}>
      <div className={className}>
        {children(isHidden)}
      </div>
    </ScrollObserverContext.Provider>
  )
}

function useScrollObserver() {
  const context = useContext(ScrollObserverContext)
  if (!context) {
    throw new Error('useScrollObserver must be used within ScrollObserver')
  }
  return context
}

export function TriggerGroup({ children, className }: { children: ReactNode, className?: string }) {
  return <div className={className}>{children}</div>
}

export function Trigger({ 
  id, 
  children, 
  className 
}: { 
  id: string
  children: (isActive: boolean) => ReactNode
  className?: string 
}) {
  const { registerTrigger, unregisterTrigger, activeTrigger } = useScrollObserver()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (ref.current) {
      registerTrigger(id, ref.current)
      return () => unregisterTrigger(id)
    }
  }, [id, registerTrigger, unregisterTrigger])

  const isActive = activeTrigger === id

  return (
    <div ref={ref} className={className}>
      {children(isActive)}
    </div>
  )
}

export function ReactorGroup({ children, className }: { children: ReactNode, className?: string }) {
  return <div className={className}>{children}</div>
}

export function Reactor({ 
  id, 
  children, 
  className 
}: { 
  id: string
  children: (isActive: boolean) => ReactNode
  className?: string 
}) {
  const { registerReactor, unregisterReactor, activeTrigger } = useScrollObserver()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (ref.current) {
      registerReactor(id, ref.current)
      return () => unregisterReactor(id)
    }
  }, [id, registerReactor, unregisterReactor])

  const isActive = activeTrigger === id

  return (
    <div ref={ref} className={className}>
      {children(isActive)}
    </div>
  )
}

// Attach sub-components
ScrollObserver.TriggerGroup = TriggerGroup
ScrollObserver.Trigger = Trigger
ScrollObserver.ReactorGroup = ReactorGroup
ScrollObserver.Reactor = Reactor
