import React, { useState } from 'react';

function App() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [history, setHistory] = useState([]);
  const [currentSlot, setCurrentSlot] = useState(null);
  const [context, setContext] = useState({});
  const [bestProduct, setBestProduct] = useState(null);
  const [passesPolicy, setPassesPolicy] = useState(null);
  const [policyReason, setPolicyReason] = useState('');
  const [sessionId] = useState(crypto.randomUUID());
  const [products, setProducts] = useState([]);

  const handleSubmit = async () => {
    if (!input) return;
    try {
      const res = await fetch('http://localhost:5000/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input, session_id: sessionId, current_slot: currentSlot }),
      });
      const data = await res.json();
      setResponse(data.response);
      setCurrentSlot(data.current_slot);
      setContext(data.context);
      setBestProduct(data.best_product);
      setPassesPolicy(data.passes_policy);
      setPolicyReason(data.policy_reason);
      setProducts(data.products || extractProductsFromResponse(data.response));
      setHistory(data.history || [...history, { user: input, bot: data.response, intent: data.intent, context: data.context }]);
      setInput('');
    } catch (err) {
      console.error('Submission error:', err);
      setResponse('❌ Failed to connect to the server');
    }
  };

  const extractProductsFromResponse = (text) => {
    const matches = text.matchAll(/\| (.*?) \| \$(.*?) \| (.*?) \| \[View\]\((.*?)\) \| (.*?) \| (.*?) \| (.*?) \|/g);
    return [...matches].map((m) => ({
      title: m[1],
      price: parseFloat(m[2]),
      match_score: parseFloat(m[3]),
      link: m[4],
      availability: m[5],
      delivery_time: m[6],
      category: m[7],
    }));
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && input) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleOrder = () => {
    setResponse(`✅ Order initiated for "${bestProduct.title}"!`);
  };

  const handleApproval = async () => {
    try {
      const res = await fetch('http://localhost:5000/api/approval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();
      window.open(data.mailto_link, '_blank'); // Automatically open mail link
    } catch (err) {
      console.error('Approval error:', err);
      setResponse('❌ Failed to generate approval link');
    }
  };

  const handleExit = () => {
    setResponse('👋 Goodbye! The assistant has been reset.');
    setInput('');
    setCurrentSlot(null);
    setContext({});
    setBestProduct(null);
    setPassesPolicy(null);
    setPolicyReason('');
    setProducts([]);
    setHistory([]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-100 flex flex-col items-center py-8 px-4">
      <h1 className="text-3xl font-bold mb-4 text-blue-800">🛍️ Conversational Buying Assistant</h1>
      <div className="w-full max-w-3xl">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder={
            currentSlot
              ? `Enter ${currentSlot.charAt(0).toUpperCase() + currentSlot.slice(1)}`
              : 'e.g., I need a laptop for college work under $500'
          }
          className="w-full p-3 border border-gray-300 rounded shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400 mb-2"
        />
        <button
          onClick={handleSubmit}
          disabled={!input}
          className={`w-full px-4 py-2 rounded mb-4 font-semibold transition-all duration-300 shadow ${
            input ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          Submit {currentSlot ? 'Response' : ''}
        </button>

        {products.length > 0 && (
          <div className="overflow-x-auto mb-6">
            <h2 className="text-lg font-semibold mb-3 text-blue-700">🎯 Top Product Suggestions</h2>
            <table className="min-w-full bg-white rounded shadow text-sm border border-gray-200">
              <thead className="bg-blue-100 text-blue-800">
                <tr>
                  <th className="border px-4 py-2">Title</th>
                  <th className="border px-4 py-2">Price</th>
                  <th className="border px-4 py-2">Match Score</th>
                  <th className="border px-4 py-2">Availability</th>
                  <th className="border px-4 py-2">Delivery</th>
                  <th className="border px-4 py-2">Category</th>
                  <th className="border px-4 py-2">Link</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p, idx) => (
                  <tr
                    key={idx}
                    className={p.title === bestProduct?.title ? 'bg-green-100 font-semibold' : ''}
                  >
                    <td className="border px-4 py-2">{p.title}</td>
                    <td className="border px-4 py-2">${p.price.toFixed(2)}</td>
                    <td className="border px-4 py-2">{p.match_score?.toFixed(2)}</td>
                    <td className="border px-4 py-2">{p.availability}</td>
                    <td className="border px-4 py-2">{p.delivery_time}</td>
                    <td className="border px-4 py-2">{p.category}</td>
                    <td className="border px-4 py-2">
                      <a
                        href={p.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 underline hover:text-blue-800"
                      >
                        View
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {response && (
          <div className="mb-4 bg-white p-4 rounded shadow-md text-gray-800 whitespace-pre-wrap border-l-4 border-blue-500">
            {response}
          </div>
        )}

        {bestProduct && !currentSlot && (
          <div className="mb-4">
            {passesPolicy ? (
              <button
                onClick={handleOrder}
                className="bg-green-500 text-white px-4 py-2 rounded shadow hover:bg-green-600 transition-all duration-200"
              >
                ✅ Order Now
              </button>
            ) : (
              <button
                onClick={handleApproval}
                className="bg-yellow-500 text-white px-4 py-2 rounded shadow hover:bg-yellow-600 transition-all duration-200"
              >
                ✉️ Mail Approver
              </button>
            )}
            {!passesPolicy && policyReason && (
              <p className="text-red-600 mt-2 font-semibold">{policyReason}</p>
            )}
          </div>
        )}

        <button
          onClick={handleExit}
          className="bg-red-500 text-white px-4 py-2 rounded mt-4 shadow hover:bg-red-600 transition-all duration-200"
        >
          🔁 Reset
        </button>

        {history.length > 0 && (
          <div className="mt-6">
            <h2 className="text-xl font-semibold mb-2 text-blue-800">🗨️ Conversation History</h2>
            {history.map((entry, idx) => (
              <div key={idx} className="bg-white p-3 shadow rounded mb-2 border border-gray-200">
                <p>
                  <strong>You:</strong> {entry.user}
                </p>
                {(entry.intent === 'initial' || entry.intent === 'clarification') && entry.context && (
                  <p className="text-gray-600 text-sm italic">
                    <strong>Extracted:</strong> Item = {entry.context.item}
                    {entry.context.budget && `, Budget = $${entry.context.budget.toFixed(2)}`}
                    {entry.context.purpose && `, Purpose = ${entry.context.purpose}`}
                    {entry.context.brand && `, Brand = ${entry.context.brand}`}
                    {entry.context.features && `, Features = ${entry.context.features}`}
                    {entry.context.urgency && `, Urgency = ${entry.context.urgency}`}
                  </p>
                )}
                <p>
                  <strong>Assistant:</strong> {entry.bot}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
