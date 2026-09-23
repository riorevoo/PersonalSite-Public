import styles from './UserBubble.module.css'

interface UserBubbleProps {
  text: string
}

export function UserBubble({ text }: UserBubbleProps) {
  return (
    <div className={styles.bubble}>
      <p className={styles.text}>{text}</p>
    </div>
  )
}
