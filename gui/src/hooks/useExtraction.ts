import { useState, useCallback, useRef } from 'react'

export const ExtractionStatus = {
    IDLE: 'idle',
    RUNNING: 'running',
    COMPLETE: 'complete',
    ERROR: 'error'
} as const

export type ExtractionStatus = typeof ExtractionStatus[keyof typeof ExtractionStatus]

export interface Progress {
    phase: string
    commentsFetched: number
    expansionsRemaining: number
    matchesFound: number
    percent: number
}

export interface QAAnswer {
    id: string
    author: string
    body: string
    created_utc: number
    permalink: string
}

export interface QAPair {
    question: {
        id: string
        author: string
        body: string
        created_utc: number
        permalink: string
    }
    answers: QAAnswer[]
}

export interface ExtractionResult {
    submissionId: string
    submissionTitle: string
    totalComments: number
    qaPairs: QAPair[]
}

interface ExtractionParams {
    threadUrl: string
    accounts: string[]
    includeTimestamps: boolean
    includeCommentIds: boolean
}

const API_BASE = 'http://localhost:8000'

export function useExtraction() {
    const [status, setStatus] = useState<ExtractionStatus>(ExtractionStatus.IDLE)
    const [progress, setProgress] = useState<Progress>({
        phase: 'Idle',
        commentsFetched: 0,
        expansionsRemaining: 0,
        matchesFound: 0,
        percent: 0
    })
    const [result, setResult] = useState<ExtractionResult | null>(null)
    const [error, setError] = useState<string | null>(null)

    const eventSourceRef = useRef<EventSource | null>(null)

    const parseSubmissionId = (input: string): string => {
        // Handle full URL
        const urlMatch = input.match(/comments\/([a-z0-9]+)/i)
        if (urlMatch) return urlMatch[1]

        // Handle short URL
        const shortMatch = input.match(/redd\.it\/([a-z0-9]+)/i)
        if (shortMatch) return shortMatch[1]

        // Assume it's already an ID
        return input.trim()
    }

    const startExtraction = useCallback(async (params: ExtractionParams) => {
        const submissionId = parseSubmissionId(params.threadUrl)

        if (!submissionId) {
            setError('Invalid thread URL or ID')
            setStatus(ExtractionStatus.ERROR)
            return
        }

        setStatus(ExtractionStatus.RUNNING)
        setError(null)
        setResult(null)
        setProgress({
            phase: 'Starting...',
            commentsFetched: 0,
            expansionsRemaining: 0,
            matchesFound: 0,
            percent: 0
        })

        try {
            // Start extraction job
            const response = await fetch(`${API_BASE}/api/extract`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    submission_id: submissionId,
                    accounts: params.accounts
                })
            })

            if (!response.ok) {
                const errData = await response.json()
                throw new Error(errData.detail || 'Failed to start extraction')
            }

            const { job_id } = await response.json()

            // Connect to SSE for progress updates
            eventSourceRef.current = new EventSource(`${API_BASE}/api/progress/${job_id}`)

            eventSourceRef.current.onmessage = (event) => {
                const data = JSON.parse(event.data)

                if (data.type === 'progress') {
                    setProgress({
                        phase: data.phase,
                        commentsFetched: data.comments_fetched,
                        expansionsRemaining: data.expansions_remaining,
                        matchesFound: data.matches_found,
                        percent: data.percent
                    })
                } else if (data.type === 'complete') {
                    setResult({
                        submissionId: data.submission_id,
                        submissionTitle: data.submission_title,
                        totalComments: data.total_comments,
                        qaPairs: data.qa_pairs
                    })
                    setStatus(ExtractionStatus.COMPLETE)
                    eventSourceRef.current?.close()
                } else if (data.type === 'error') {
                    setError(data.message)
                    setStatus(ExtractionStatus.ERROR)
                    eventSourceRef.current?.close()
                }
            }

            eventSourceRef.current.onerror = () => {
                setError('Connection to server lost')
                setStatus(ExtractionStatus.ERROR)
                eventSourceRef.current?.close()
            }

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error')
            setStatus(ExtractionStatus.ERROR)
        }
    }, [])

    const reset = useCallback(() => {
        eventSourceRef.current?.close()
        setStatus(ExtractionStatus.IDLE)
        setProgress({
            phase: 'Idle',
            commentsFetched: 0,
            expansionsRemaining: 0,
            matchesFound: 0,
            percent: 0
        })
        setResult(null)
        setError(null)
    }, [])

    return {
        status,
        progress,
        result,
        error,
        startExtraction,
        reset
    }
}
