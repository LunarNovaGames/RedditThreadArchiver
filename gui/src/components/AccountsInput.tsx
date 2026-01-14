interface AccountsInputProps {
    value: string
    onChange: (value: string) => void
    disabled?: boolean
}

export function AccountsInput({ value, onChange, disabled }: AccountsInputProps) {
    return (
        <div className="input-group">
            <label htmlFor="accounts">Accounts to Capture</label>
            <textarea
                id="accounts"
                value={value}
                onChange={e => onChange(e.target.value)}
                disabled={disabled}
                placeholder="LarSwen
Larian_Swen
larianstudios"
            />
            <span className="helper-text">
                One username per line, or comma-separated. Only replies from these accounts will be captured.
            </span>
        </div>
    )
}
