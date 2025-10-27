import React, { useState, useRef, useEffect } from 'react';

// Access Lucide icons from global scope (for browser environment)
const { 
    Send, 
    Menu, 
    MessageSquare, 
    Briefcase, 
    GraduationCap, 
    DollarSign, 
    Home 
} = typeof lucideReact !== 'undefined' ? lucideReact : {};

// Main App Component
const App = () => {
    // State to hold the chat messages
    const [messages, setMessages] = useState([
        { 
            text: "Hello! I am the Anurag University Assistant. I can help you with Admissions, Academics, Placements, and Facilities. How can I assist you today?", 
            sender: 'bot',
            timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
        }
    ]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const chatEndRef = useRef(null);

    // Scroll to the bottom of the chat window on new message
    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    // FastAPI/Ngrok URL setup
    const FASTAPI_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://127.0.0.1:8000' 
        : 'https://YOUR_NGROK_URL.ngrok.io';

    const CHAT_ENDPOINT = `${FASTAPI_URL}/chat`;

    // Function to handle sending the message
    const handleSendMessage = async (textToSend = inputMessage) => {
        if (!textToSend.trim() || isLoading) return;

        // 1. Add user message to state
        const userMessage = { 
            text: textToSend, 
            sender: 'user', 
            timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) 
        };
        setMessages(prevMessages => [...prevMessages, userMessage]);
        setInputMessage('');
        setIsLoading(true);

        try {
            // 2. Send message to FastAPI endpoint
            const response = await fetch(CHAT_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: textToSend })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // 3. Add bot response to state
            const botMessage = {
                text: data.response || "Sorry, I couldn't find a direct answer. Try asking about Admissions, Placements, Academics, or Facilities.",
                sender: 'bot',
                timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
            };
            setMessages(prevMessages => [...prevMessages, botMessage]);

        } catch (error) {
            console.error("Error communicating with chatbot API:", error);
            const errorMessage = {
                text: "My apologies, there was an issue connecting to the knowledge service. Please check the backend server status (FastAPI/Ngrok).",
                sender: 'bot',
                timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
            };
            setMessages(prevMessages => [...prevMessages, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    // Quick links for testing categories
    const quickLinks = [
        { icon: DollarSign, text: "B.Tech Fee", query: "What is the tuition fee for B.Tech?" },
        { icon: GraduationCap, text: "UG Programs", query: "What courses are offered for undergraduate?" },
        { icon: Briefcase, text: "Avg Salary", query: "What is the average placement salary?" },
        { icon: Home, text: "Hostel Fee", query: "How much is the hostel fee for boys?" },
    ];

    return (
        <div className="flex flex-col h-full bg-gray-50 font-inter antialiased">
            {/* Header */}
            <header className="flex items-center justify-between p-4 bg-indigo-700 shadow-lg text-white">
                <div className="flex items-center space-x-3">
                    <MessageSquare className="w-6 h-6" />
                    <h1 className="text-xl font-bold">Anurag UniBot (ES)</h1>
                </div>
                <Menu className="w-6 h-6 md:hidden cursor-pointer" />
            </header>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
                
                {/* Left Panel (Quick Links) - Hidden on Mobile */}
                <aside className="hidden md:flex w-full md:w-1/4 bg-white border-r border-gray-200 p-4 flex-col space-y-4">
                    <h2 className="text-lg font-semibold text-gray-800 border-b pb-2 mb-2">Quick Access Categories</h2>
                    {quickLinks.map((link, index) => (
                        <button
                            key={index}
                            onClick={() => handleSendMessage(link.query)}
                            disabled={isLoading}
                            className="flex items-center w-full px-3 py-2 text-left text-sm font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition duration-150 ease-in-out disabled:opacity-50"
                        >
                            <link.icon className="w-5 h-5 mr-3 flex-shrink-0" />
                            {link.text}
                        </button>
                    ))}
                    <p className="pt-4 text-xs text-gray-500 italic">
                        Try asking in Hindi or Telugu!
                        <br/>(e.g., "హాస్టల్ ఫీజు ఎంత?")
                    </p>
                </aside>

                {/* Right Panel (Chat Window) */}
                <main className="flex-1 flex flex-col p-4 overflow-y-auto max-h-screen">
                    
                    {/* Message History */}
                    <div className="flex-1 overflow-y-auto space-y-4 p-4 md:p-6 bg-white shadow-inner rounded-xl max-w-4xl w-full mx-auto">
                        {messages.map((message, index) => (
                            <div 
                                key={index} 
                                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div className={`max-w-xs md:max-w-md lg:max-w-lg px-4 py-3 rounded-2xl shadow-md transition-all duration-300 ease-in-out 
                                    ${message.sender === 'user' 
                                        ? 'bg-indigo-500 text-white rounded-br-none' 
                                        : 'bg-white border border-gray-200 text-gray-800 rounded-tl-none'
                                    }`}
                                >
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.text}</p>
                                    <span className={`block mt-1 text-right text-xs ${message.sender === 'user' ? 'text-indigo-200' : 'text-gray-400'}`}>
                                        {message.timestamp}
                                    </span>
                                </div>
                            </div>
                        ))}
                        {/* Loading Indicator */}
                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="bg-white border border-gray-200 text-gray-600 px-4 py-3 rounded-2xl rounded-tl-none shadow-md">
                                    <div className="flex space-x-1">
                                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-75"></div>
                                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-150"></div>
                                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-300"></div>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="mt-4 pt-4 border-t border-gray-200 max-w-4xl w-full mx-auto">
                        <div className="flex space-x-3">
                            <input
                                type="text"
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                                disabled={isLoading}
                                placeholder="Ask a question about Admissions, Placements, or Facilities..."
                                className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100 transition duration-150 shadow-sm"
                            />
                            <button
                                onClick={() => handleSendMessage()}
                                disabled={!inputMessage.trim() || isLoading}
                                className="p-3 bg-indigo-600 text-white rounded-xl shadow-lg hover:bg-indigo-700 transition duration-150 ease-in-out disabled:opacity-50 flex items-center justify-center"
                            >
                                {isLoading ? (
                                    <span className="animate-spin h-5 w-5 border-t-2 border-white rounded-full"></span>
                                ) : (
                                    <Send className="w-5 h-5" />
                                )}
                            </button>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
};

// Make App available globally for the HTML file to access
if (typeof window !== 'undefined') {
    window.App = App;
}

export default App;