import React, { useState, useEffect, useRef } from 'react';
import {
  createTheme, ThemeProvider,
  Box, Paper, TextField, IconButton,
  Typography, Button, Table, TableHead, TableRow, TableCell, TableBody
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    background: { default: '#121212' },
    primary: { main: '#90caf9' },
    secondary: { main: '#f48fb1' }
  },
  typography: {
    fontFamily: 'Roboto, sans-serif',
  }
});

function App() {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState([]);
  const [currentSlot, setCurrentSlot] = useState(null);
  const [context, setContext] = useState({});
  const [bestProduct, setBestProduct] = useState(null);
  const [passesPolicy, setPassesPolicy] = useState(null);
  const [policyReason, setPolicyReason] = useState('');
  const [products, setProducts] = useState([]);
  const [sessionId] = useState(crypto.randomUUID());

  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history]);

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

  const handleSubmit = async () => {
    if (!input.trim()) return;
    const userMessage = input;
    setInput('');
    setHistory((prev) => [...prev, { type: 'user', text: userMessage }]);

    try {
      const res = await fetch('http://localhost:5000/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: userMessage, session_id: sessionId, current_slot: currentSlot }),
      });
      const data = await res.json();

      setCurrentSlot(data.current_slot);
      setContext(data.context);
      setBestProduct(data.best_product);
      setPassesPolicy(data.passes_policy);
      setPolicyReason(data.policy_reason);
      setProducts(data.products || extractProductsFromResponse(data.response));
      setHistory((prev) => [...prev, { type: 'bot', text: data.response }]);
    } catch (err) {
      console.error(err);
      setHistory((prev) => [...prev, { type: 'bot', text: '❌ Failed to connect to server' }]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleOrder = () => {
    setHistory((prev) => [...prev, {
      type: 'bot',
      text: `✅ Order initiated for "${bestProduct.title}"!`
    }]);
  };

  const handleApproval = async () => {
    try {
      const res = await fetch('http://localhost:5000/api/approval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();
      window.open(data.mailto_link, '_blank');
    } catch (err) {
      console.error(err);
      setHistory((prev) => [...prev, { type: 'bot', text: '❌ Failed to generate approval link' }]);
    }
  };

  const handleExit = () => {
    setHistory([{ type: 'bot', text: '👋 Assistant has been reset.' }]);
    setInput('');
    setCurrentSlot(null);
    setContext({});
    setBestProduct(null);
    setPassesPolicy(null);
    setPolicyReason('');
    setProducts([]);
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <Box sx={{ height: '100vh', display: 'flex', justifyContent: 'center', bgcolor: 'background.default', width: '100vw' }}>
        <Box sx={{ py: 2, px: 2, flex: 1, display: 'flex', flexDirection: 'column', width: '58%' }}>
          <Typography variant="h5" align="center" gutterBottom color="primary">
            🛍️ Conversational Buying Assistant
          </Typography>

          <Paper elevation={3} sx={{ flex: 1, p: 2, overflowY: 'auto', mb: 2, borderRadius: 2 }}>
            {history.map((msg, idx) => {
              const tableRegex = /\| Title \|.*?\|\n(\|.*\|\n)+/s;
              const tableMatch = msg.type === 'bot' && tableRegex.exec(msg.text);
              const tableData = [];

              if (tableMatch) {
                const lines = tableMatch[0].split('\n').filter((line) => line.startsWith('|'));
                const headers = lines[0].split('|').map((h) => h.trim()).filter(Boolean);
                const rows = lines.slice(2).map((line) =>
                  line.split('|').map((cell) => cell.trim()).filter(Boolean)
                );
                rows.forEach((row) => {
                  const entry = {};
                  headers.forEach((h, i) => {
                    entry[h] = row[i];
                  });
                  tableData.push(entry);
                });

                // Extract text before and after the table
                const [beforeTable, afterTable] = msg.text.split(tableMatch[0]);
                const preTableText = beforeTable.trim();
                const explanationText = afterTable ? afterTable.trim() : '';

                return (
                  <Box key={idx} display="flex" justifyContent="flex-start" mb={1}>
                    <Box
                      sx={{
                        bgcolor: 'grey.800',
                        color: '#eee',
                        p: 1.5,
                        borderRadius: 2,
                        maxWidth: '80%',
                        whiteSpace: 'pre-wrap',
                        overflowX: 'auto'
                      }}
                    >
                      {preTableText && (
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          {preTableText}
                        </Typography>
                      )}
                      <Table size="small" sx={{ backgroundColor: '#212121', borderRadius: 1, mb: 2 }}>
                        <TableHead>
                          <TableRow>
                            {Object.keys(tableData[0]).map((header) => (
                              <TableCell key={header} sx={{ color: '#90caf9' }}>{header}</TableCell>
                            ))}
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {tableData.map((row, rIdx) => (
                            <TableRow key={rIdx} sx={bestProduct && row.Title === bestProduct.title ? { backgroundColor: '#2e7d32' } : {}}>
                              {Object.entries(row).map(([key, value], cIdx) => (
                                <TableCell key={cIdx} sx={{ color: '#fff' }}>
                                  {key === 'Link' && value.includes('http') ? (
                                    <a href={value.match(/\((.*?)\)/)?.[1]} target="_blank" rel="noreferrer" style={{ color: '#90caf9' }}>
                                      View
                                    </a>
                                  ) : (
                                    value
                                  )}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                      {explanationText && (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{explanationText}</ReactMarkdown>
                      )}
                    </Box>
                  </Box>
                );
              }

              return (
                <Box key={idx} display="flex" justifyContent={msg.type === 'user' ? 'flex-end' : 'flex-start'} mb={1}>
                  <Box
                    sx={{
                      bgcolor: msg.type === 'user' ? 'primary.main' : 'grey.800',
                      color: msg.type === 'user' ? '#fff' : '#eee',
                      p: 1.5,
                      borderRadius: 2,
                      maxWidth: '80%',
                      whiteSpace: 'pre-wrap',
                      overflowX: 'auto'
                    }}
                  >
                    <Typography variant="body2">{msg.text}</Typography>
                  </Box>
                </Box>
              );
            })}
            <div ref={chatEndRef} />
          </Paper>

          {bestProduct && !currentSlot && (
            <Box mb={2} textAlign="center">
              {passesPolicy ? (
                <Button variant="contained" color="success" onClick={handleOrder}>
                  ✅ Order Now
                </Button>
              ) : (
                <Button variant="contained" color="warning" onClick={handleApproval}>
                  ✉️ Mail Approver
                </Button>
              )}
              {!passesPolicy && policyReason && (
                <Typography variant="body2" color="error" mt={1}>{policyReason}</Typography>
              )}
            </Box>
          )}

          <Box display="flex" gap={1}>
            <TextField
              fullWidth
              placeholder={currentSlot ? `Enter ${currentSlot}` : 'Type your request...'}
              variant="outlined"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              size="small"
            />
            <IconButton onClick={handleSubmit} disabled={!input.trim()} color="primary">
              <SendIcon />
            </IconButton>
          </Box>

          <Button
            startIcon={<RestartAltIcon />}
            color="error"
            onClick={handleExit}
            sx={{ mt: 1, alignSelf: 'center' }}
          >
            Reset
          </Button>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;