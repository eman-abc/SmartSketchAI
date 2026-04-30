import { useCallback, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Sidebar from '../components/Sidebar';
import TopBar from '../components/Topbar';
import Workspace from '../components/Workspace';
import RightPanel from '../components/RightPanel';
import type { GenerateResult } from '../types';

function Home() {
  const { isAuthenticated } = useAuth();
  const [generateResult, setGenerateResult] = useState<GenerateResult | null>(null);
  const [currentPrompt, setCurrentPrompt] = useState('');
  const [selectedImage, setSelectedImage] = useState<GenerateResult | null>(null);

  const handleGenerateResult = useCallback(
    (result: GenerateResult | null, prompt: string) => {
      setGenerateResult(result);
      setCurrentPrompt(prompt);
      setSelectedImage(null);
    },
    []
  );

  const handleSelectHistory = useCallback((image: GenerateResult) => {
    setSelectedImage(image);
    setGenerateResult(image);
    setCurrentPrompt(image.prompt);
  }, []);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="h-screen flex flex-col bg-white dark:bg-gray-900">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar onSelectImage={handleSelectHistory} />
        <Workspace
          onGenerateResult={handleGenerateResult}
          selectedImage={selectedImage}
        />
        <RightPanel
          generateResult={generateResult}
          prompt={currentPrompt}
        />
      </div>
    </div>
  );
}

export default Home;
