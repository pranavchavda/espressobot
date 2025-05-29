import React, { useState, useEffect } from 'react';
import { Form, useActionData, useNavigation } from '@remix-run/react';
import { Button } from "@common/button";
import { Textarea } from "@common/textarea";
import { Field, Label } from "@common/fieldset";
import { Input } from "@common/input";
import { InfoIcon } from 'lucide-react';

function ProfilePage({ user }) { // User prop from Remix loader
  const actionData = useActionData();
  const navigation = useNavigation();

  const [name, setName] = useState(user?.name || '');
  const [bio, setBio] = useState(user?.bio || '');

  // Update state if user prop changes (e.g., after successful save and re-load)
  useEffect(() => {
    setName(user?.name || '');
    setBio(user?.bio || '');
  }, [user]);

  const isSaving = 
    navigation.state === 'submitting' &&
    navigation.formMethod === 'PUT' &&
    navigation.formAction.endsWith('/api/profile');

  // Display general messages (success or top-level errors)
  const generalMessage = actionData?.message;
  const generalError = actionData?.errors && typeof actionData.errors === 'string' ? actionData.errors : null;


  return (
    <div className="container mx-auto p-4 max-w-lg">
      <h1 className="text-2xl font-semibold mb-6 text-zinc-800 dark:text-zinc-200">Your Profile</h1>
      
      {generalMessage && !generalError && (
        <div className="mb-4 p-3 bg-green-100 text-green-700 border border-green-400 rounded">
          {generalMessage}
        </div>
      )}
      {generalError && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 border border-red-400 rounded">
          {generalError}
        </div>
      )}

      <Form method="put" action="/api/profile" className="space-y-6">
        <Field>
          <Label htmlFor="name">Name</Label>
          <Input
            type="text"
            name="name"
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isSaving}
          />
          {actionData?.errors?.name && (
            <p className="text-red-500 text-xs mt-1">{actionData.errors.name}</p>
          )}
        </Field>

        <Field>
          <Label htmlFor="email">Email (cannot be changed)</Label>
          <Input
            type="email"
            name="email_display" // Name changed to avoid submission
            id="email_display"
            value={user?.email || ''}
            readOnly
            disabled // Always disabled
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
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="Tell us a little about yourself..."
            disabled={isSaving}
          />
          {actionData?.errors?.bio && (
            <p className="text-red-500 text-xs mt-1">{actionData.errors.bio}</p>
          )}
        </Field>

        <Field>
          <Button type="submit" disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </Field>
      </Form>
    </div>
  );
}

export default ProfilePage;
