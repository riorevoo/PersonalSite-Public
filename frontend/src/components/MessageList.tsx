import { useEffect, useRef } from 'react'
import type { Message } from '../hooks/useChat'
import { AnswerCard } from './AnswerCard'
import styles from './MessageList.module.css'
import { UserBubble } from './UserBubble'

interface MessageListProps {
  messages: Message[]
  onRetry: (id: number) => void
}

export function MessageList({ messages, onRetry }: MessageListProps) {
  const listRef = useRef<HTMLDivElement>(null)

  // After a question is sent or its answer arrives, bring the newest exchange into view. An
  // answer taller than the scroll area is shown from its first line rather than its last.
  useEffect(() => {
    if (messages.length === 0) return
    const exchange = listRef.current?.lastElementChild
    const answer = exchange?.lastElementChild
    const scrollArea = listRef.current?.closest('main') ?? listRef.current?.parentElement
    if (!exchange || !answer) return

    if (scrollArea && answer.getBoundingClientRect().height > scrollArea.clientHeight) {
      answer.scrollIntoView({ block: 'start' })
    } else {
      exchange.scrollIntoView({ block: 'end' })
    }
  }, [messages])

  return (
    <div
      ref={listRef}
      className={styles.list}
      role="log"
      aria-live="polite"
      aria-label="Conversation"
    >
      {messages.map((message) => (
        <div key={message.id} className={styles.exchange}>
          <UserBubble text={message.question} />
          <AnswerCard
            status={message.status}
            text={message.answer}
            onRetry={() => onRetry(message.id)}
          />
        </div>
      ))}
    </div>
  )
}
