import React from 'react';
import { NavLink } from 'react-router-dom';

const Header: React.FC = () => {
  return (
    <header className="text-cosmic-latte p-4" style={{ backgroundColor: '#1a1f35' }}>
      <div className="container mx-auto flex justify-between items-center">
        <h1 className="text-xl font-bold">DeviationEngine</h1>
        <nav>
          <ul className="flex items-center list-none p-0 m-0">
            <li className="ml-6">
              <NavLink to="/" className={({ isActive }) => `pb-1 border-b-2 ${isActive ? 'border-blue-400 text-blue-300' : 'border-transparent hover:border-blue-300'}`}>
                Home
              </NavLink>
            </li>
            <li className="ml-6">
              <NavLink to="/console" className={({ isActive }) => `pb-1 border-b-2 ${isActive ? 'border-blue-400 text-blue-300' : 'border-transparent hover:border-blue-300'}`}>
                Deviation Console
              </NavLink>
            </li>
            <li className="ml-6">
              <NavLink to="/library" className={({ isActive }) => `pb-1 border-b-2 ${isActive ? 'border-blue-400 text-blue-300' : 'border-transparent hover:border-blue-300'}`}>
                Timeline Library
              </NavLink>
            </li>
            {/* <li className="ml-6">
              <NavLink to="/reports" className={({ isActive }) => `pb-1 border-b-2 ${isActive ? 'border-blue-400 text-blue-300' : 'border-transparent hover:border-blue-300'}`}>
                Report View
              </NavLink>
            </li> */}
            <li className="ml-6">
              <NavLink to="/about" className={({ isActive }) => `pb-1 border-b-2 ${isActive ? 'border-blue-400 text-blue-300' : 'border-transparent hover:border-blue-300'}`}>
                About
              </NavLink>
            </li>
            <li className="ml-6">
              <NavLink to="/settings" className={({ isActive }) => `pb-1 border-b-2 ${isActive ? 'border-blue-400 text-blue-300' : 'border-transparent hover:border-blue-300'}`}>
                ⚙️ Settings
              </NavLink>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
};

export default Header;