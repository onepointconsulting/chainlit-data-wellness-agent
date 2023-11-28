import { useEffect } from "react"

/**
 * Added by Gil Fernandes
 * Capture the user id from the URL.
 * @returns 
 */
export default function captureUserId() : string | null {
    const params = new URLSearchParams(window.location.search)
    const id: string | null = params.get("id")
    if (!!id) {
        console.info(`Id '${id}' available`)
    }
    return id
}
