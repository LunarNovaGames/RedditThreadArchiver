import { ExtractionStatus } from '../hooks/useExtraction'
import type { Progress } from '../hooks/useExtraction'

interface ProgressPanelProps {
    status: ExtractionStatus
    progress: Progress
    error: string | null
}

export function ProgressPanel({ status, progress, error }: ProgressPanelProps) {
    const isIdle = status === ExtractionStatus.IDLE
    const isRunning = status === ExtractionStatus.RUNNING
    const isComplete = status === ExtractionStatus.COMPLETE
    const isError = status === ExtractionStatus.ERROR

    const getPhaseText = () => {
        if (isIdle) return 'Waiting to start...'
        if (isComplete) return 'Extraction complete!'
        if (isError) return 'Extraction failed'
        return progress.phase
    }

    const getPhaseClass = () => {
        if (isRunning) return 'phase-indicator running'
        if (isComplete) return 'phase-indicator complete'
        if (isError) return 'phase-indicator error'
        return 'phase-indicator'
    }

    return (
        <div className={`progress-panel ${isIdle ? 'idle' : ''}`}>
            <h3>Progress</h3>

            <div className="progress-stats">
                <div className="stat-item">
                    <span className="label">Comments</span>
                    <span className="value">{progress.commentsFetched.toLocaleString()}</span>
                </div>
                <div className="stat-item">
                    <span className="label">Expansions</span>
                    <span className="value">{progress.expansionsRemaining.toLocaleString()}</span>
                </div>
                <div className="stat-item">
                    <span className="label">Q&A Matches</span>
                    <span className="value">{progress.matchesFound.toLocaleString()}</span>
                </div>
                <div className="stat-item">
                    <span className="label">Progress</span>
                    <span className="value">{progress.percent}%</span>
                </div>
            </div>

            <div className="progress-bar-container">
                <div
                    className="progress-bar"
                    style={{ width: `${progress.percent}%` }}
                />
            </div>

            <div className={getPhaseClass()}>
                {getPhaseText()}
            </div>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}
        </div>
    )
}
