import type { ProfileFact } from '../content/profile'
import styles from './FactsTable.module.css'

interface FactsTableProps {
  facts: ProfileFact[]
}

export function FactsTable({ facts }: FactsTableProps) {
  return (
    <dl className={styles.table}>
      {facts.map((fact) => (
        <div key={fact.label} className={styles.row}>
          <dt className={styles.label}>{fact.label}</dt>
          <dd className={styles.value}>{fact.value}</dd>
        </div>
      ))}
    </dl>
  )
}
