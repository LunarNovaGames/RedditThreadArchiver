interface ThreadInputProps {
    value: string
    onChange: (value: string) => void
    disabled?: boolean
}

export function ThreadInput({ value, onChange, disabled }: ThreadInputProps) {
    return (
        <div className="input-group">
            <label htmlFor="thread-url">Thread URL or ID</label>
            <input
                id="thread-url"
                type="text"
                value={value}
                onChange={e => onChange(e.target.value)}
                disabled={disabled}
                placeholder="https://reddit.com/r/Games/comments/1q870w5/... or just 1q870w5"
            />
            <span className="helper-text">
                Paste a Reddit thread URL or submission ID
            </span>
        </div>
    )
}
