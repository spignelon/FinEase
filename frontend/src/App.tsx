import React, { useState } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginForm from './components/Auth/LoginForm';
import RegisterForm from './components/Auth/RegisterForm';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Portfolio from './components/Portfolio';
import Trading from './components/Trading';
import TradeHistory from './components/TradeHistory';

const AppContent: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [currentView, setCurrentView] = useState('dashboard');

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return isLogin ? (
      <LoginForm onToggleMode={() => setIsLogin(false)} />
    ) : (
      <RegisterForm onToggleMode={() => setIsLogin(true)} />
    );
  }

  const renderCurrentView = () => {
    switch (currentView) {
      case 'portfolio':
        return <Portfolio />;
      case 'trading':
        return <Trading />;
      case 'history':
        return <TradeHistory />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <Layout currentView={currentView} onViewChange={setCurrentView}>
      {renderCurrentView()}
    </Layout>
  );
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;