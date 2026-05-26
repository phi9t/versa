interface OpenQuestionsProps {
  questions: string[]
}

export default function OpenQuestions({ questions }: OpenQuestionsProps) {
  if (questions.length === 0) {
    return <p className="text-muted">No blocking questions.</p>
  }

  return (
    <ul className="questions-list">
      {questions.map((question) => (
        <li key={question}>{question}</li>
      ))}
    </ul>
  )
}
