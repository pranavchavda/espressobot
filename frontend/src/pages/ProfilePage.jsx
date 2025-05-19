import React, { useState, useEffect } from 'react';
import { Button } from "@common/button";
import { Textarea } from "@common/textarea";
import { Field, Label } from "@common/fieldset";
import { Input } from "@common/input";
import { InfoIcon } from 'lucide-react';

function ProfilePage() {
  const [profile, setProfile] = useState({ name: '', email: '', bio: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/profile');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setProfile(data);
      } catch (e) {
        console.error("Failed to fetch profile:", e);
        setError('Failed to load profile data. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfile(prevProfile => ({
      ...prevProfile,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMessage('');
    try {
      const response = await fetch('/api/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: profile.name, bio: profile.bio }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setSuccessMessage(data.message || 'Profile updated successfully!');
      // Optionally re-fetch profile or assume backend reflects changes
    } catch (e) {
      console.error("Failed to update profile:", e);
      setError(e.message || 'Failed to update profile. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !profile.email) { // Show full page loader only on initial load
    return <div className="p-4 text-center">Loading profile...</div>;
  }

  return (
    <div className="container mx-auto p-4 max-w-lg">
      <h1 className="text-2xl font-semibold mb-6 text-zinc-800 dark:text-zinc-200">Your Profile</h1>
      
      {error && <div className="mb-4 p-3 bg-red-100 text-red-700 border border-red-400 rounded">{error}</div>}
      {successMessage && <div className="mb-4 p-3 bg-green-100 text-green-700 border border-green-400 rounded">{successMessage}</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Field>
          <Label htmlFor="name">
            Name
          </Label>
          <Input
            type="text"
            name="name"
            id="name"
            value={profile.name || ''}
            onChange={handleChange}
          />
        </Field>

        <Field>
          <Label htmlFor="email">
            Email (cannot be changed)
          </Label>
          <Input
            type="email"
            name="email"
            id="email"
            value={profile.email || ''}
            readOnly
            disabled
            cursor="not-allowed"
            className="bg-zinc-100 dark:bg-zinc-700 text-zinc-500 dark:text-zinc-400 cursor-not-allowed"
          />
        </Field>

        <Field>
          <Label htmlFor="bio" className="flex items-center gap-2">
            Bio
            <span className="relative group inline-block">
                <InfoIcon className="w-4 h-4 text-zinc-400 hover:text-zinc-600 dark:text-zinc-500 dark:hover:text-zinc-300 cursor-none" />
              <span className="absolute z-10 mt-2 w-64 -translate-x-1/2 rounded bg-zinc-900 px-3 py-2 text-xs text-white opacity-0 group-hover:opacity-100 transition pointer-events-none dark:bg-zinc-800 shadow-lg">
                What you enter here will be visible to EspressoBot. EspressoBot may use this information to better understand you and provide more personalized responses.
              </span>
            </span>
          </Label>
          <Textarea
            name="bio"
            id="bio"
            rows="4"
            value={profile.bio || ''}
            onChange={handleChange}
            placeholder="Tell us a little about yourself..."
          />
        </Field>

        <Field>
          <Button
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? 'Saving...' : 'Save Changes'}
          </Button>
        </Field>
      </form>
    </div>
  );
}

export default ProfilePage;
