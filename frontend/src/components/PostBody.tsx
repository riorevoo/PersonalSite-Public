import Markdown from 'react-markdown'
import styles from './PostBody.module.css'

interface PostBodyProps {
  /** The post as Markdown. Raw HTML in it is shown as text, never run. */
  markdown: string
}

export function PostBody({ markdown }: PostBodyProps) {
  return (
    <div className={styles.body}>
      <Markdown>{markdown}</Markdown>
    </div>
  )
}
