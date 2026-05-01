import { useCallback, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Sidebar from '../components/Sidebar';
import TopBar from '../components/Topbar';
import Workspace from '../components/Workspace';
import RightPanel from '../components/RightPanel';
import type { GenerateResult, ForensicLogEntry } from '../types';

function Home() {
  const { isAuthenticated } = useAuth();
  const [generateResult, setGenerateResult] = useState<GenerateResult | null>(null);
  const [currentPrompt, setCurrentPrompt] = useState('');
  const [selectedImage, setSelectedImage] = useState<GenerateResult | null>(null);
  const [forensicLogs, setForensicLogs] = useState<ForensicLogEntry[]>([]);
  const [workspaceKey, setWorkspaceKey] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateResult = useCallback(
    (result: GenerateResult | null, promptText: string) => {
      setGenerateResult(result);
      setCurrentPrompt(promptText);
      setSelectedImage(null);
    },
    []
  );

  const handleSelectHistory = useCallback((image: GenerateResult) => {
    setSelectedImage(image);
    setGenerateResult(image);
    setCurrentPrompt(image.prompt);
  }, []);

  const handleNewSession = useCallback(() => {
    setGenerateResult(null);
    setCurrentPrompt('');
    setSelectedImage(null);
    setForensicLogs([]);
    setWorkspaceKey((k) => k + 1);
  }, []);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex min-h-screen flex-col bg-forensic-studio text-text-high antialiased">
      <TopBar onNewSession={handleNewSession} />
      <div className="mx-auto flex w-full max-w-[1920px] min-h-0 flex-1 gap-6 px-4 pb-6 pt-6 sm:px-6">
        <Sidebar onSelectImage={handleSelectHistory} />
        <Workspace
          key={workspaceKey}
          onGenerateResult={handleGenerateResult}
          selectedImage={selectedImage}
          onStreamLogsChange={setForensicLogs}
          onLoadingChange={setIsGenerating}
        />
        <RightPanel
          generateResult={generateResult}
          prompt={currentPrompt}
          onUpdateResult={(res) =>
            handleGenerateResult(res as GenerateResult, currentPrompt)
          }
          forensicLogs={forensicLogs}
          isGenerating={isGenerating}
        />
      </div>
    </div>
  );
}

export default Home;
