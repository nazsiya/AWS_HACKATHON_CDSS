import { useState } from 'react';
import { isMockMode } from '../../api/config';
import { postAgent } from '../../api/client';
import { useActivity } from '../../context/ActivityContext';
import './AIChat.css';

const welcomePrompts = [
    { icon: '📊', text: 'Patient Summary', desc: 'Get a quick summary of any patient' },
    { icon: '💊', text: 'Drug Interactions', desc: 'Check medication compatibility' },
    { icon: '📋', text: 'Treatment Plans', desc: 'AI-generated treatment protocols' },
    { icon: '🔬', text: 'Lab Interpretation', desc: 'Analyze lab results and trends' },
];

export default function AIChat() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const { logActivity } = useActivity();

    const handleSend = (text) => {
        const msg = text || input;
        if (!msg.trim()) return;

        setMessages(prev => [...prev, { role: 'user', text: msg, time: 'Now' }]);
        setInput('');
        setIsTyping(true);
        logActivity('ai_chat');

        if (!isMockMode()) {
            postAgent({ message: msg, history: messages })
                .then((res) => {
                    // Supervisor returns { data: { reply, safety_disclaimer }, safety_disclaimer, ... }
                    const inner = res?.data;
                    const reply = (inner && inner.reply) ?? res?.reply ?? res?.message ?? res?.response ?? res?.body;
                    const text = typeof reply === 'string' ? reply : (reply?.text ?? JSON.stringify(reply ?? {}));
                    const disclaimer = inner?.safety_disclaimer ?? res?.safety_disclaimer;
                    setMessages(prev => [...prev, {
                        role: 'assistant',
                        text,
                        time: 'Now',
                        ...(disclaimer ? { safety_disclaimer: disclaimer } : {}),
                    }]);
                })
                .catch((err) => {
                    setMessages(prev => [...prev, {
                        role: 'assistant',
                        text: `Error: ${err.message || 'Failed to get AI response.'}`,
                        time: 'Now',
                    }]);
                })
                .finally(() => setIsTyping(false));
            return;
        }

        setTimeout(() => {
            setIsTyping(false);
            const responses = {
                'Patient Summary': "📊 **Patient Summary Request**\n\nPlease specify a patient name or ID. I can provide:\n• Complete medical history\n• Active medications & interactions\n• Recent lab results & trends\n• AI-generated risk assessment\n\nFor example, try: \"Summarize Rajesh Kumar's history\"",
                'Drug Interactions': "💊 **Drug Interaction Checker Ready**\n\nI can analyze drug interactions using the Clinical Protocols MCP. Please provide the medications you'd like to check.\n\n**Quick checks available:**\n• Warfarin + Aspirin → ⚠️ HIGH bleeding risk\n• Metformin + Amlodipine → ✅ Safe\n• Digoxin + Amiodarone → ⚠️ Toxicity risk",
                'Treatment Plans': "📋 **Treatment Plan Generator**\n\nI can generate evidence-based treatment plans for:\n• Hypertension management\n• Diabetes (Type 1 & 2) protocols\n• Post-surgical care pathways\n• Chronic disease management\n\nSpecify the condition and patient context to get started.",
                'Lab Interpretation': "🔬 **Lab Analysis Engine**\n\nI can interpret lab results including:\n• CBC, LFT, KFT, Lipid Panel\n• HbA1c trends with glycemic control assessment\n• Cardiac markers (Troponin, BNP)\n• Coagulation studies (PT/INR)\n\nShare the lab values or patient ID for analysis.",
            };

            setMessages(prev => [...prev, {
                role: 'assistant',
                text: responses[msg] || "I've analyzed your query using the RAG pipeline. Based on the clinical knowledge base and patient records, here's what I found:\n\n✅ Your request has been processed successfully. The analysis considers evidence-based guidelines, patient history, and current medication profiles.\n\nWould you like me to elaborate on any specific aspect, or shall I generate a formal report?",
                time: 'Now',
            }]);
        }, 1500);
    };

    return (
        <div className="ai-chat-page page-enter">
            <div className="ai-chat-page__header">
                <div className="ai-chat-page__avatar">🤖</div>
                <div className="ai-chat-page__info">
                    <div className="ai-chat-page__title">CDSS AI Assistant</div>
                    <div className="ai-chat-page__desc">Powered by Amazon Bedrock · Claude 3 Haiku · RAG-enhanced</div>
                </div>
                <span className="ai-chat-page__model">Claude 3 Haiku</span>
            </div>

            <div className="ai-chat-page__messages">
                {messages.length === 0 ? (
                    <div className="ai-welcome">
                        <div className="ai-welcome__emoji">🧠</div>
                        <div className="ai-welcome__title">How can I assist you today?</div>
                        <div className="ai-welcome__subtitle">
                            I can help with patient summaries, drug interactions, treatment plans, and clinical decision support.
                        </div>
                        <div className="ai-welcome__prompts">
                            {welcomePrompts.map((p, i) => (
                                <button
                                    key={i}
                                    className={`ai-welcome__prompt animate-in animate-in-delay-${i + 1}`}
                                    onClick={() => handleSend(p.text)}
                                >
                                    <div className="ai-welcome__prompt-icon">{p.icon}</div>
                                    <div className="ai-welcome__prompt-text">{p.text}</div>
                                    <div className="ai-welcome__prompt-desc">{p.desc}</div>
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <>
                        {messages.map((msg, i) => (
                            <div key={i} className={`ai-message ai-message--${msg.role}`}>
                                <div className="ai-message__bubble">{msg.text}</div>
                                {msg.safety_disclaimer && (
                                    <div className="ai-message__disclaimer" role="note">
                                        {msg.safety_disclaimer}
                                    </div>
                                )}
                                <div className="ai-message__time">{msg.time}</div>
                            </div>
                        ))}
                        {isTyping && (
                            <div className="ai-typing">
                                <div className="ai-typing__dot" />
                                <div className="ai-typing__dot" />
                                <div className="ai-typing__dot" />
                            </div>
                        )}
                    </>
                )}
            </div>

            <div className="ai-chat-page__input-area">
                <button className="ai-chat-page__voice-btn" title="Voice input">🎤</button>
                <input
                    className="ai-chat-page__input"
                    type="text"
                    placeholder="Ask anything about patients, medications, protocols..."
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSend()}
                />
                <button className="ai-chat-page__send-btn" onClick={() => handleSend()}>↑</button>
            </div>
        </div>
    );
}
