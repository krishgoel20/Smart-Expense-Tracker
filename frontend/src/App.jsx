import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [authMode, setAuthMode] = useState('login')
  const [authForm, setAuthForm] = useState({ username: '', password: '' })
  const [authError, setAuthError] = useState('')

  const [transactions, setTransactions] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalTransactions, setTotalTransactions] = useState(0)
  const [categorySummary, setCategorySummary] = useState([])
  const [monthlySummary, setMonthlySummary] = useState([])
  const [uploadFile, setUploadFile] = useState(null)
  const [statusMessage, setStatusMessage] = useState('')

  const authHeaders = () => ({ Authorization: `Bearer ${token}` })

  const fetchTransactions = (pageNum = page) => {
    fetch(`http://127.0.0.1:8000/transactions?page=${pageNum}&page_size=10`, {
      headers: authHeaders()
    })
      .then(res => res.json())
      .then(data => {
        setTransactions(data.transactions)
        setTotalPages(data.total_pages)
        setTotalTransactions(data.total)
        setPage(data.page)
      })
      .catch(err => console.error('Failed to fetch transactions:', err))
  }

  const fetchSummaries = () => {
    fetch('http://127.0.0.1:8000/summary/by-category', { headers: authHeaders() })
      .then(res => res.json())
      .then(data => setCategorySummary(data))

    fetch('http://127.0.0.1:8000/summary/monthly', { headers: authHeaders() })
      .then(res => res.json())
      .then(data => setMonthlySummary(data))
  }

  useEffect(() => {
    if (token) {
      fetchTransactions()
      fetchSummaries()
    }
  }, [token])

  const handleAuth = () => {
    const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register'
    setAuthError('')

    fetch(`http://127.0.0.1:8000${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(authForm)
    })
      .then(res => {
        if (!res.ok) throw new Error('Invalid username or password')
        return res.json()
      })
      .then(data => {
        localStorage.setItem('token', data.access_token)
        setToken(data.access_token)
      })
      .catch(err => setAuthError(err.message))
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
  }

  const handleUpload = () => {
    if (!uploadFile) {
      setStatusMessage('Please select a file first.')
      return
    }
    const formData = new FormData()
    formData.append('file', uploadFile)

    fetch('http://127.0.0.1:8000/upload', {
      method: 'POST',
      headers: authHeaders(),
      body: formData
    })
      .then(res => res.json())
      .then(data => {
        setStatusMessage(data.message)
        fetchTransactions()
        fetchSummaries()
      })
      .catch(err => setStatusMessage('Upload failed: ' + err.message))
  }

  const handleCategorize = () => {
    setStatusMessage('Categorizing...')
    fetch('http://127.0.0.1:8000/categorize', {
      method: 'POST',
      headers: authHeaders()
    })
      .then(res => res.json())
      .then(data => {
        setStatusMessage(data.message)
        fetchTransactions()
        fetchSummaries()
      })
      .catch(err => setStatusMessage('Categorization failed: ' + err.message))
  }

  const maxCategorySpend = Math.max(...categorySummary.map(c => c.total_spent), 1)
  const thisMonth = monthlySummary[0]

  if (!token) {
    return (
      <div className="app auth-screen">
        <h1>Smart Expense Tracker</h1>
        <div className="auth-card">
          <h3>{authMode === 'login' ? 'Log In' : 'Register'}</h3>
          <input
            type="text"
            placeholder="Username"
            value={authForm.username}
            onChange={e => setAuthForm({ ...authForm, username: e.target.value })}
          />
          <input
            type="password"
            placeholder="Password"
            value={authForm.password}
            onChange={e => setAuthForm({ ...authForm, password: e.target.value })}
          />
          <button onClick={handleAuth}>{authMode === 'login' ? 'Log In' : 'Register'}</button>
          {authError && <p className="status-message">{authError}</p>}
          <p className="auth-toggle" onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}>
            {authMode === 'login' ? "Don't have an account? Register" : 'Already have an account? Log in'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <div className="app-header">
        <h1>Smart Expense Tracker</h1>
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </div>
      <p className="txn-count">{totalTransactions} transactions logged</p>

      <div className="summary-cards">
        <div className="summary-card spend">
          <div className="label">This Month's Spend</div>
          <div className="value">₹{thisMonth?.total_spent ?? 0}</div>
        </div>
        <div className="summary-card income">
          <div className="label">This Month's Income</div>
          <div className="value">₹{thisMonth?.total_income ?? 0}</div>
        </div>
      </div>

      <div className="controls">
        <input type="file" accept=".csv" onChange={e => setUploadFile(e.target.files[0])} />
        <button onClick={handleUpload}>Upload CSV</button>
        <button onClick={handleCategorize}>Categorize Pending</button>
      </div>
      {statusMessage && <p className="status-message">{statusMessage}</p>}

      <h3>Spending by Category</h3>
      <div className="ledger">
        {categorySummary.map(cat => (
          <div className="ledger-row" key={cat.category}>
            <span className="cat-name">{cat.category}</span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${(cat.total_spent / maxCategorySpend) * 100}%` }}
              />
            </div>
            <span className="cat-amount">₹{cat.total_spent}</span>
          </div>
        ))}
      </div>

      <h3>Transactions</h3>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Merchant</th>
            <th>Amount</th>
            <th>Type</th>
            <th>Category</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map(txn => (
            <tr key={txn.id}>
              <td>{txn.txn_date}</td>
              <td>{txn.raw_description}</td>
              <td>{txn.merchant_name || '-'}</td>
              <td className="amount">₹{txn.amount}</td>
              <td>{txn.txn_type}</td>
              <td>{txn.category || 'Uncategorized'}</td>
              <td><span className={`badge ${txn.category_source}`}>{txn.category_source}</span></td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pagination">
        <button onClick={() => fetchTransactions(page - 1)} disabled={page <= 1}>
          Previous
        </button>
        <span>Page {page} of {totalPages}</span>
        <button onClick={() => fetchTransactions(page + 1)} disabled={page >= totalPages}>
          Next
        </button>
      </div>
    </div>
  )
}

export default App