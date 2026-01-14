import { useState, useCallback } from 'react'
import type { ExtractionResult } from '../hooks/useExtraction'

interface ExportSectionProps {
    result: ExtractionResult
    includeTimestamps: boolean
    includeCommentIds: boolean
}

type ExportFormat = 'json' | 'text'

export function ExportSection({ result, includeTimestamps, includeCommentIds }: ExportSectionProps) {
    const [format, setFormat] = useState<ExportFormat>('json')
    const [copySuccess, setCopySuccess] = useState(false)

    const generateOutput = useCallback(() => {
        if (format === 'json') {
            const output = {
                metadata: {
                    submission_id: result.submissionId,
                    submission_title: result.submissionTitle,
                    extracted_at: new Date().toISOString(),
                    total_comments: result.totalComments,
                    qa_pairs: result.qaPairs.length
                },
                qa_pairs: result.qaPairs.map(qa => ({
                    question: {
                        ...(includeCommentIds && { id: qa.question.id }),
                        author: qa.question.author,
                        body: qa.question.body,
                        ...(includeTimestamps && { created_utc: qa.question.created_utc }),
                        permalink: qa.question.permalink
                    },
                    answers: qa.answers.map(a => ({
                        ...(includeCommentIds && { id: a.id }),
                        author: a.author,
                        body: a.body,
                        ...(includeTimestamps && { created_utc: a.created_utc }),
                        permalink: a.permalink
                    }))
                }))
            }
            return JSON.stringify(output, null, 2)
        } else {
            // Plain text format
            let output = ''
            for (const qa of result.qaPairs) {
                output += 'Q:\n'
                output += qa.question.body + '\n\n'
                for (const answer of qa.answers) {
                    output += 'A:\n'
                    output += answer.body + '\n\n'
                }
                output += '\n'
            }
            return output
        }
    }, [result, format, includeTimestamps, includeCommentIds])

    const handleSave = useCallback(() => {
        const content = generateOutput()
        const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `reddit_qa_${result.submissionId}.${format === 'json' ? 'json' : 'txt'}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }, [generateOutput, format, result.submissionId])

    const handleCopy = useCallback(async () => {
        const content = generateOutput()
        await navigator.clipboard.writeText(content)
        setCopySuccess(true)
        setTimeout(() => setCopySuccess(false), 2000)
    }, [generateOutput])

    return (
        <div className="export-section">
            <h3>Export ({result.qaPairs.length} Q&A pairs)</h3>

            <div className="format-selector">
                <label className="format-option">
                    <input
                        type="radio"
                        name="format"
                        value="json"
                        checked={format === 'json'}
                        onChange={() => setFormat('json')}
                    />
                    JSON
                </label>
                <label className="format-option">
                    <input
                        type="radio"
                        name="format"
                        value="text"
                        checked={format === 'text'}
                        onChange={() => setFormat('text')}
                    />
                    Plain Text
                </label>
            </div>

            <div className="export-buttons">
                <button className="export-btn primary" onClick={handleSave}>
                    Save to File
                </button>
                <button className="export-btn" onClick={handleCopy}>
                    Copy to Clipboard
                </button>
            </div>

            {copySuccess && (
                <div className="copy-success">Copied to clipboard!</div>
            )}
        </div>
    )
}
